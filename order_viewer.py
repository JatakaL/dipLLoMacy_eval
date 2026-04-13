#!/usr/bin/env python3
"""
Order Viewer for Diplomacy — visualize unit orders on the map.

Renders a map image with order overlays:
- Arrows for movement orders (source → destination)
- Hold shields for holding units
- Dashed arrows for support and convoy orders
- Color-coded results (green=success, red=bounce/failed, gray=pending)
- Build (★) and disband (✕) markers for winter orders

Input formats:
  1. JSON turn result (dict with "resolved_orders", as produced by GameModerator.run_turn)
  2. Text turn summary (as produced by format_turn_summary)

Usage:
    python order_viewer.py --map map.json --orders turn_result.json [--output orders.png]
    python order_viewer.py --map map.json --orders turn_summary.txt [--output orders.png]
"""

import json
import re
import sys
import argparse
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np


# ---------------------------------------------------------------------------
# Result → color mapping
# ---------------------------------------------------------------------------
RESULT_COLORS = {
    "success": "#2ca02c",       # green
    "bounce": "#d62728",        # red
    "dislodged": "#d62728",     # red
    "no_path": "#d62728",       # red
    "cut": "#ff7f0e",           # orange
    "pending": "#7f7f7f",       # gray
    "invalid_format": "#7f7f7f",
    "invalid_unit": "#7f7f7f",
    "invalid_target": "#7f7f7f",
    "invalid_adjacent": "#7f7f7f",
    "invalid_unit_type": "#7f7f7f",
}

# Display names for power colors (reused from game_manager)
POWER_NAMES = [
    "Avalon", "Borealis", "Crimson", "Dawnland", "Eastmark",
    "Frostheim", "Greenwood", "Highvale", "Ironhold", "Jadekeep",
]

# ---------------------------------------------------------------------------
# Turn-summary text parser
# ---------------------------------------------------------------------------

# Matches a single order line inside the text turn summary.
# E.g.  "      A {Province2} H  [success]"
#        "      F {Calm Sound} M {North Strait}  [bounce]"
#        "      A {Harell} S A {Karwyn} M {Falmere}  [success]"
#        "      B A {Province1}  [success]"
_ORDER_LINE_RE = re.compile(
    r'^\s+'                            # leading whitespace
    r'(?P<order_text>.+?)'             # the order text
    r'\s+\[(?P<result>[^\]]+)\]\s*$'   # [result] at end
)

_POWER_HEADER_RE = re.compile(r'^\s{2,6}(\S.+?):\s*$')


def parse_turn_summary_text(text: str) -> list[dict]:
    """Parse the text produced by ``format_turn_summary`` into order dicts.

    Returns a list of dicts compatible with the JSON ``resolved_orders``
    format (keys: unit_type, location, order_type, target, result, power, …).
    """
    from game.orders import OrderParser, OrderType

    orders: list[dict] = []
    current_power: Optional[str] = None
    in_orders_section = False

    for line in text.splitlines():
        stripped = line.strip()

        if stripped == "Orders:":
            in_orders_section = True
            continue

        # Detect end of orders section
        if in_orders_section and stripped and not stripped.startswith(("A ", "F ", "B ")) and ":" in stripped:
            # Could be a new section header like "Unit positions:"
            if not _POWER_HEADER_RE.match(line):
                in_orders_section = False
                continue

        if not in_orders_section:
            continue

        # Power header
        power_match = _POWER_HEADER_RE.match(line)
        if power_match:
            current_power = power_match.group(1)
            continue

        # Order line
        order_match = _ORDER_LINE_RE.match(line)
        if not order_match:
            continue

        order_text = order_match.group("order_text").strip()
        result_str = order_match.group("result").strip()

        # Handle BUILD orders that start with "B"
        if order_text.startswith("B "):
            build_match = re.match(r'^B\s+(A|F)\s+\{([^}]+)\}', order_text)
            if build_match:
                od = {
                    "unit_type": build_match.group(1),
                    "location": build_match.group(2),
                    "order_type": "build",
                    "target": None,
                    "support_unit_type": None,
                    "support_from": None,
                    "support_to": None,
                    "result": result_str,
                    "power": current_power,
                    "raw_order": order_text,
                }
                orders.append(od)
            continue

        parsed = OrderParser.parse(order_text)
        od = parsed.to_dict()
        od["result"] = result_str
        od["power"] = current_power
        orders.append(od)

    return orders


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def load_orders(filepath: str) -> tuple[list[dict], str]:
    """Load orders from a JSON or text file.

    Returns ``(orders_list, turn_label)``.
    """
    path = Path(filepath)
    raw = path.read_text()

    # Try JSON first
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            turn_label = data.get("turn", "")
            resolved = data.get("resolved_orders", [])
            return resolved, turn_label
        # Might be a bare list
        if isinstance(data, list):
            return data, ""
    except json.JSONDecodeError:
        pass

    # Fall back to text parsing
    orders = parse_turn_summary_text(raw)
    # Try to extract turn label from the text
    turn_match = re.search(r'TURN:\s*(.+)', raw)
    turn_label = turn_match.group(1).strip() if turn_match else ""
    return orders, turn_label


def _build_name_to_id_map(faces: dict) -> dict[str, str]:
    """Build a mapping from territory name → face ID."""
    mapping: dict[str, str] = {}
    for face_id, face_data in faces.items():
        name = face_data.get("name")
        if name:
            mapping[name] = face_id
        # Also map ID to itself
        mapping[face_id] = face_id
    return mapping


# ---------------------------------------------------------------------------
# Polygon reconstruction (mirrored from GameManager._get_face_polygon)
# ---------------------------------------------------------------------------

def _get_face_polygon(
    face_id: str,
    faces: dict,
    borders: dict,
    edges: dict,
    vertex_coords: dict,
) -> list[list[float]]:
    """Reconstruct a face polygon from topology data."""
    face_data = faces.get(face_id, {})
    face_edges: list[str] = []
    for border_id in face_data.get("borders", []):
        if border_id in borders:
            face_edges.extend(borders[border_id].get("edges", []))

    if not face_edges:
        return []

    vertex_graph: dict[str, list[str]] = {}
    for edge_id in face_edges:
        if edge_id not in edges:
            continue
        edge = edges[edge_id]
        v1, v2 = edge["v1"], edge["v2"]
        vertex_graph.setdefault(v1, []).append(v2)
        vertex_graph.setdefault(v2, []).append(v1)

    if not vertex_graph:
        return []

    start = next(iter(vertex_graph))
    polygon: list[list[float]] = []
    current = start
    visited: set[str] = set()

    for _ in range(len(vertex_graph) + 1):
        if current in visited:
            break
        visited.add(current)
        if current in vertex_coords:
            polygon.append(vertex_coords[current])

        next_v = None
        for nb in vertex_graph.get(current, []):
            if nb not in visited:
                next_v = nb
                break
        if next_v is None:
            break
        current = next_v

    return polygon


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_order_view(
    map_data: dict,
    orders: list[dict],
    turn_label: str = "",
    output_path: Optional[str] = None,
    dpi: int = 150,
    ownership: Optional[dict[str, str]] = None,
    prev_ownership: Optional[dict[str, str]] = None,
) -> str:
    """Render the base map with order overlays and save to *output_path*.

    Args:
        map_data: Parsed map JSON (Phase 7 output).
        orders: List of order dicts (``resolved_orders`` format).
        turn_label: Turn identifier string for the title.
        output_path: Destination PNG path.  Defaults to ``orders_view.png``.
        dpi: Output resolution.
        ownership: Optional mapping of ``face_id → power`` reflecting
            current territory control.  When provided, overrides the
            static ``face_data["owner"]`` used for polygon colouring.
        prev_ownership: Optional mapping of ``face_id → power`` from the
            previous turn.  Used together with *ownership* to render
            hatching on territories that changed hands.

    Returns:
        The path where the image was saved.
    """
    if output_path is None:
        output_path = "orders_view.png"

    topology = map_data.get("topology", {})
    faces = topology.get("faces", {})
    borders_data = topology.get("borders", {})
    edges_data = topology.get("edges", {})
    vertices_list = topology.get("vertices", [])
    vertex_coords = {v["id"]: v["coords"] for v in vertices_list}

    powers_data = map_data.get("powers", {})
    power_list = sorted(powers_data.keys()) if powers_data else []

    # Power → color
    tableau = list(mcolors.TABLEAU_COLORS.values())
    power_colors = {p: tableau[i % len(tableau)] for i, p in enumerate(power_list)}

    name_to_id = _build_name_to_id_map(faces)

    terrain_colors = {
        "land": "#C5E0B4",
        "sea": "#BDD7EE",
        "impassable": "#A6A6A6",
    }

    fig, ax = plt.subplots(figsize=(14, 12))

    # --- Draw base map polygons -------------------------------------------
    for face_id, face_data in faces.items():
        polygon = _get_face_polygon(face_id, faces, borders_data, edges_data, vertex_coords)
        if not polygon or len(polygon) < 3:
            continue
        poly_arr = np.array(polygon)

        face_type = face_data.get("type", "land")
        if ownership is not None:
            owner = ownership.get(face_id, face_data.get("owner"))
        else:
            owner = face_data.get("owner")
        is_sc = face_data.get("is_supply_center", False)

        if owner and owner in power_colors:
            color = power_colors[owner]
            alpha = 0.65
        elif is_sc and face_type == "land":
            color = "#FFE699"
            alpha = 0.7
        else:
            color = terrain_colors.get(face_type, "gray")
            alpha = 0.5 if face_type == "land" else 0.6

        ax.fill(poly_arr[:, 0], poly_arr[:, 1],
                color=color, alpha=alpha, edgecolor="black", linewidth=0.4)

        # -- Hatching for gained territories --
        # Territory fill already uses the new owner's colour.
        # Overlay hatching in the *previous* owner's colour so the
        # viewer can see who held it before.
        if prev_ownership is not None:
            prev_owner = prev_ownership.get(face_id, face_data.get("owner"))
            if owner != prev_owner:
                if owner is not None and owner in power_colors:
                    if prev_owner and prev_owner in power_colors:
                        hatch_color = power_colors[prev_owner]
                    else:
                        hatch_color = "#C5E0B4"  # neutral land colour
                    hatch_patch = mpatches.Polygon(
                        poly_arr, closed=True,
                        facecolor="none",
                        edgecolor=hatch_color,
                        hatch="//",
                        linewidth=0.5,
                        zorder=3,
                    )
                    ax.add_patch(hatch_patch)

    # --- Supply center markers ---
    for face_id, face_data in faces.items():
        if face_data.get("is_supply_center", False):
            lp = face_data.get("label_positions", {})
            pos = lp.get("sc_position", face_data.get("center", [0.5, 0.5]))
            ax.plot(pos[0], pos[1], "o",
                    markersize=6, color="gold",
                    markeredgecolor="black", markeredgewidth=1.2, zorder=8)

    # --- Province names ---
    for face_id, face_data in faces.items():
        name = face_data.get("name", "")
        if not name:
            continue
        lp = face_data.get("label_positions", {})
        name_pos = lp.get("name_position")
        if name_pos:
            tx, ty = name_pos
        else:
            center = face_data.get("center", [0.5, 0.5])
            tx, ty = center[0], center[1]

        face_type = face_data.get("type", "land")
        if face_type == "sea":
            ax.text(tx, ty, name, ha="center", va="center",
                    fontsize=4.5, fontstyle="italic", color="#2B5797", zorder=4)
        else:
            ax.text(tx, ty, name, ha="center", va="center",
                    fontsize=4.5, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                              alpha=0.6, edgecolor="none"),
                    zorder=5)

    # --- Helper: resolve location to face center ---
    def _center(loc: str) -> Optional[tuple[float, float]]:
        fid = name_to_id.get(loc)
        if fid is None:
            return None
        fd = faces.get(fid)
        if fd is None:
            return None
        c = fd.get("center")
        if c is None:
            return None
        return (c[0], c[1])

    def _unit_pos(loc: str) -> Optional[tuple[float, float]]:
        """Get the pre-determined unit position or fall back to center."""
        fid = name_to_id.get(loc)
        if fid is None:
            return None
        fd = faces.get(fid)
        if fd is None:
            return None
        lp = fd.get("label_positions", {})
        pos = lp.get("unit_position")
        if pos:
            return (pos[0], pos[1])
        return _center(loc)

    # --- Draw order overlays ---
    _draw_orders(ax, orders, _center, _unit_pos, power_colors, name_to_id, faces)

    # --- Legend ---
    _draw_legend(ax, orders, power_list, power_colors)

    # --- Title ---
    title = "Diplomacy — Order View"
    if turn_label:
        title += f"  |  {turn_label}"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

    ax.set_aspect("equal")
    ax.axis("off")
    plt.tight_layout()

    output_path = str(output_path)
    if not output_path.lower().endswith(".png"):
        output_path += ".png"

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# Order drawing helpers
# ---------------------------------------------------------------------------

def _result_color(result: str) -> str:
    return RESULT_COLORS.get(result, "#7f7f7f")


def _is_failed(result: str) -> bool:
    return result in ("bounce", "dislodged", "no_path", "cut",
                      "invalid_format", "invalid_unit", "invalid_target",
                      "invalid_adjacent", "invalid_unit_type")


def _draw_unit_marker(
    ax: plt.Axes,
    pos: Optional[tuple[float, float]],
    unit_type: str,
    power: Optional[str],
    power_colors: dict[str, str],
) -> None:
    """Draw a unit marker (army circle or fleet triangle) at *pos*."""
    if pos is None:
        return

    unit_color = power_colors.get(power, "#555555") if power else "#555555"

    marker = "o" if unit_type == "A" else "^"
    ax.plot(pos[0], pos[1], marker,
            markersize=11, color=unit_color,
            markeredgecolor="black", markeredgewidth=1.8, zorder=15)
    ax.text(pos[0], pos[1] - (0.001 if unit_type == "F" else 0),
            unit_type, ha="center", va="center",
            fontsize=6, fontweight="bold", color="white", zorder=16)


def _draw_orders(
    ax: plt.Axes,
    orders: list[dict],
    center_fn,
    unit_pos_fn,
    power_colors: dict[str, str],
    name_to_id: dict[str, str],
    faces: dict,
) -> None:
    """Draw all order overlays onto *ax*."""
    for od in orders:
        otype = od.get("order_type", "hold")
        result = od.get("result", "pending")
        location = od.get("location", "")
        power = od.get("power")
        color = _result_color(result)
        unit_type = od.get("unit_type", "?")

        src = unit_pos_fn(location)
        src_center = center_fn(location)

        # Draw the unit marker at its starting territory for all
        # non-winter order types so the unit is always visible.
        if otype in ("move", "hold", "support", "convoy", "retreat"):
            _draw_unit_marker(ax, src, unit_type, power, power_colors)

        if otype == "move":
            _draw_move(ax, od, src, center_fn, color, result)
        elif otype == "hold":
            _draw_hold(ax, src, color)
        elif otype == "support":
            _draw_support(ax, od, src, center_fn, color)
        elif otype == "convoy":
            _draw_convoy(ax, od, src, center_fn, color)
        elif otype == "build":
            _draw_build(ax, od, unit_pos_fn, center_fn, power, power_colors)
        elif otype == "disband":
            _draw_disband(ax, od, src, color)
        elif otype == "retreat":
            _draw_move(ax, od, src, center_fn, color, result,
                       linestyle="dashed")


def _draw_move(
    ax: plt.Axes,
    od: dict,
    src: Optional[tuple[float, float]],
    center_fn,
    color: str,
    result: str,
    linestyle: str = "solid",
) -> None:
    """Draw an arrow from source to target for a MOVE or RETREAT order."""
    target = od.get("target", "")
    dst = center_fn(target)
    if src is None or dst is None:
        return

    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    dist = (dx**2 + dy**2) ** 0.5
    if dist == 0:
        return

    # Shorten arrow slightly so it doesn't overlap the destination marker
    shrink = min(0.012, dist * 0.15)
    ratio = (dist - shrink) / dist
    dx *= ratio
    dy *= ratio

    style = "Simple,tail_width=2,head_width=8,head_length=6"
    arrow = mpatches.FancyArrowPatch(
        src, (src[0] + dx, src[1] + dy),
        arrowstyle=style,
        color=color,
        linewidth=1.5,
        linestyle=linestyle,
        zorder=20,
        alpha=0.85,
    )
    ax.add_patch(arrow)

    # Mark failure with an ✕ at the destination
    if _is_failed(result):
        ax.plot(dst[0], dst[1], "x",
                markersize=12, markeredgewidth=3,
                color="#d62728", zorder=22)


def _draw_hold(
    ax: plt.Axes,
    pos: Optional[tuple[float, float]],
    color: str,
) -> None:
    """Draw a hold indicator — a ring around the unit."""
    if pos is None:
        return

    # Hold ring
    ring = plt.Circle(pos, 0.012, fill=False,
                       edgecolor=color, linewidth=2.5, linestyle="solid",
                       zorder=17, alpha=0.9)
    ax.add_patch(ring)


def _draw_support(
    ax: plt.Axes,
    od: dict,
    src: Optional[tuple[float, float]],
    center_fn,
    color: str,
) -> None:
    """Draw a dashed arrow for a support order."""
    support_to = od.get("support_to")
    support_from = od.get("support_from", "")

    # Arrow goes from the supporter towards the supported destination
    # (or towards the supported unit if it's a support-hold)
    if support_to:
        dst = center_fn(support_to)
    else:
        dst = center_fn(support_from)

    if src is None or dst is None:
        return

    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    dist = (dx**2 + dy**2) ** 0.5
    if dist == 0:
        return

    shrink = min(0.012, dist * 0.15)
    ratio = (dist - shrink) / dist

    style = "Simple,tail_width=1.5,head_width=6,head_length=5"
    arrow = mpatches.FancyArrowPatch(
        src, (src[0] + dx * ratio, src[1] + dy * ratio),
        arrowstyle=style,
        color=color,
        linewidth=1.2,
        linestyle="dashed",
        zorder=18,
        alpha=0.7,
    )
    ax.add_patch(arrow)


def _draw_convoy(
    ax: plt.Axes,
    od: dict,
    src: Optional[tuple[float, float]],
    center_fn,
    color: str,
) -> None:
    """Draw a dotted arrow for a convoy order."""
    target = od.get("target", "")
    dst = center_fn(target)

    if src is None or dst is None:
        return

    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    dist = (dx**2 + dy**2) ** 0.5
    if dist == 0:
        return

    shrink = min(0.012, dist * 0.15)
    ratio = (dist - shrink) / dist

    style = "Simple,tail_width=1.5,head_width=6,head_length=5"
    arrow = mpatches.FancyArrowPatch(
        src, (src[0] + dx * ratio, src[1] + dy * ratio),
        arrowstyle=style,
        color=color,
        linewidth=1.2,
        linestyle="dotted",
        zorder=18,
        alpha=0.7,
    )
    ax.add_patch(arrow)


def _draw_build(
    ax: plt.Axes,
    od: dict,
    unit_pos_fn,
    center_fn,
    power: Optional[str],
    power_colors: dict[str, str],
) -> None:
    """Draw a build marker — a star at the build location."""
    location = od.get("location", "")
    pos = unit_pos_fn(location) or center_fn(location)
    if pos is None:
        return

    result = od.get("result", "pending")
    color = _result_color(result)
    unit_color = power_colors.get(power, "#555555") if power else "#555555"

    # Star marker for build
    ax.plot(pos[0], pos[1], "*",
            markersize=16, color=unit_color,
            markeredgecolor=color, markeredgewidth=1.5,
            zorder=20)
    # "B" label
    ax.text(pos[0], pos[1] + 0.012, "BUILD",
            ha="center", va="bottom", fontsize=5, fontweight="bold",
            color=color, zorder=21)


def _draw_disband(
    ax: plt.Axes,
    od: dict,
    pos: Optional[tuple[float, float]],
    color: str,
) -> None:
    """Draw a disband marker — an ✕ at the unit location."""
    if pos is None:
        return

    ax.plot(pos[0], pos[1], "X",
            markersize=14, markeredgewidth=2.5,
            color=color, zorder=20)
    ax.text(pos[0], pos[1] + 0.012, "DISBAND",
            ha="center", va="bottom", fontsize=5, fontweight="bold",
            color=color, zorder=21)


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------

def _draw_legend(
    ax: plt.Axes,
    orders: list[dict],
    power_list: list[str],
    power_colors: dict[str, str],
) -> None:
    """Draw a legend for power colors and result indicators."""
    elements = []

    # Power colors
    for i, power in enumerate(power_list):
        color = power_colors[power]
        display = POWER_NAMES[i] if i < len(POWER_NAMES) else power
        elements.append(
            plt.Rectangle((0, 0), 1, 1, fc=color, label=display)
        )

    if elements:
        elements.append(plt.Line2D([0], [0], color="none", label=""))

    # Result indicators
    elements.append(plt.Line2D([0], [0], color=RESULT_COLORS["success"],
                               linewidth=3, label="Success"))
    elements.append(plt.Line2D([0], [0], color=RESULT_COLORS["bounce"],
                               linewidth=3, label="Bounce / Failed"))
    elements.append(plt.Line2D([0], [0], color=RESULT_COLORS["pending"],
                               linewidth=3, label="Pending"))

    # Check if there are winter orders
    has_build = any(o.get("order_type") == "build" for o in orders)
    has_disband = any(o.get("order_type") == "disband" for o in orders)
    if has_build:
        elements.append(plt.Line2D([0], [0], marker="*", color="w",
                                   markerfacecolor="#555", markersize=12,
                                   label="Build"))
    if has_disband:
        elements.append(plt.Line2D([0], [0], marker="X", color="w",
                                   markerfacecolor="#d62728", markersize=10,
                                   label="Disband"))

    if elements:
        ax.legend(handles=elements, loc="upper left",
                  bbox_to_anchor=(0, 1), fontsize=8, framealpha=0.9)


# ---------------------------------------------------------------------------
# Public API aliases for reuse by game_viewer.py and other tools
# ---------------------------------------------------------------------------

build_name_to_id_map = _build_name_to_id_map
draw_orders = _draw_orders
draw_legend = _draw_legend


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize Diplomacy orders on the map.",
    )
    parser.add_argument("--map", required=True,
                        help="Path to map JSON file (Phase 7 output)")
    parser.add_argument("--orders", required=True,
                        help="Path to turn result JSON or text summary file")
    parser.add_argument("--output", default=None,
                        help="Output PNG path (default: orders_view.png)")
    parser.add_argument("--dpi", type=int, default=150,
                        help="Output resolution (default: 150)")
    args = parser.parse_args()

    # Load map
    with open(args.map, "r") as f:
        map_data = json.load(f)

    # Load orders
    orders, turn_label = load_orders(args.orders)

    if not orders:
        print("Warning: no orders found in the input file.", file=sys.stderr)

    out = render_order_view(
        map_data,
        orders,
        turn_label=turn_label,
        output_path=args.output,
        dpi=args.dpi,
    )
    print(f"Order view saved to {out}")


if __name__ == "__main__":
    main()
