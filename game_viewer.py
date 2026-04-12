#!/usr/bin/env python3
"""
Game Viewer — unified interface for replaying Diplomacy games.

Launch the viewer by pointing it at a game output directory produced by
the standardized export (see ``game/game_export.py``)::

    python game_viewer.py outputs/game_20260408_224500

The viewer presents a **single unified view**:

* **Map with order overlays** as the focal point — territories colored
  by owner, units shown, and order arrows/markers rendered directly on
  the map (move arrows, hold rings, support dashes, build stars, etc.).
* **Collapsible side panel** with text orders and turn summary that can
  be shown/hidden so the map gets maximum screen space.
* **Turn navigation** — Previous / Next buttons and a turn list sidebar
  to click through the game turn by turn.

The interface is built on tkinter + matplotlib (consistent with the
existing ``map_viewer.py``) and reuses ``order_viewer.py`` rendering
functions for the order overlays.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Imports — we try to import GUI libraries but gracefully handle headless
# environments so the module can still be imported for its helper functions.
# ---------------------------------------------------------------------------
_HAS_GUI = True
try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.image as mpimg
    import matplotlib.colors as mcolors
    import matplotlib.patches as mpatches
    import numpy as np
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except (ImportError, RuntimeError):
    _HAS_GUI = False

# Project imports
sys.path.insert(0, str(Path(__file__).parent))
from game.game_export import load_game_output


# ===================================================================
# Game Viewer GUI
# ===================================================================

class GameViewer:
    """Tkinter-based Game Viewer for Diplomacy game replays.

    Presents a single unified view with the map + order overlays as the
    focal point and a collapsible text panel on the right for orders and
    the turn summary.

    Args:
        game_dir: Path to a standardized game output directory.
    """

    def __init__(self, game_dir: str | Path) -> None:
        if not _HAS_GUI:
            raise RuntimeError(
                "GUI libraries (tkinter, matplotlib with TkAgg) are required "
                "to run the Game Viewer interactively."
            )

        self.game_data = load_game_output(game_dir)
        self.turns = self.game_data["turns"]
        self.metadata = self.game_data["metadata"]
        self.map_data = self.game_data["map_data"]
        self.result = self.game_data["result"]
        self.current_turn_idx = 0
        self._side_panel_visible = True

        # Pre-compute map helpers for live rendering
        self._init_map_helpers()

        # ----- Root window -----
        self.root = tk.Tk()
        self.root.title(f"Diplomacy Game Viewer — {Path(game_dir).name}")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 650)

        self._build_ui()
        self._update_display()

    # ------------------------------------------------------------------
    # Map helper initialisation (for live rendering of orders on map)
    # ------------------------------------------------------------------

    def _init_map_helpers(self) -> None:
        """Pre-compute topology lookups used by the order-overlay renderer."""
        topology = self.map_data.get("topology", {})
        self._faces = topology.get("faces", {})
        self._borders_data = topology.get("borders", {})
        self._edges_data = topology.get("edges", {})
        vertices_list = topology.get("vertices", [])
        self._vertex_coords = {v["id"]: v["coords"] for v in vertices_list}

        powers_data = self.map_data.get("powers", {})
        power_list = sorted(powers_data.keys()) if powers_data else []
        tableau = list(mcolors.TABLEAU_COLORS.values())
        self._power_colors = {
            p: tableau[i % len(tableau)] for i, p in enumerate(power_list)
        }
        self._power_list = power_list

        # name → face-ID mapping
        self._name_to_id: dict[str, str] = {}
        for fid, fd in self._faces.items():
            name = fd.get("name")
            if name:
                self._name_to_id[name] = fid
            self._name_to_id[fid] = fid

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Assemble all widgets."""
        # ---------- Top info / nav bar ----------
        top_frame = ttk.Frame(self.root, padding=4)
        top_frame.pack(fill=tk.X)

        # Navigation controls on the left
        self.prev_btn = ttk.Button(top_frame, text="◀ Prev", command=self._prev_turn)
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.turn_label_var = tk.StringVar(value="")
        ttk.Label(
            top_frame,
            textvariable=self.turn_label_var,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(side=tk.LEFT, padx=8)

        self.next_btn = ttk.Button(top_frame, text="Next ▶", command=self._next_turn)
        self.next_btn.pack(side=tk.LEFT, padx=(4, 16))

        # Game result summary
        if self.result:
            winner = self.result.get("winner") or "No winner"
            ttk.Label(
                top_frame,
                text=f"Result: {winner}  ({self.result.get('turns_played', '?')} turns)",
                font=("TkDefaultFont", 10, "italic"),
            ).pack(side=tk.LEFT, padx=8)

        # Toggle side panel button (right side)
        self.toggle_btn = ttk.Button(
            top_frame, text="Hide Panel ▷", command=self._toggle_side_panel
        )
        self.toggle_btn.pack(side=tk.RIGHT, padx=4)

        # ---------- Main content area ----------
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # --- Left strip: turn list ---
        turn_list_frame = ttk.Frame(self.main_paned, width=170)
        self.main_paned.add(turn_list_frame, weight=0)

        ttk.Label(
            turn_list_frame, text="Turns", font=("TkDefaultFont", 10, "bold")
        ).pack(pady=(0, 2))

        list_inner = ttk.Frame(turn_list_frame)
        list_inner.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_inner, orient=tk.VERTICAL)
        self.turn_listbox = tk.Listbox(
            list_inner,
            yscrollcommand=scrollbar.set,
            font=("TkFixedFont", 9),
            selectmode=tk.SINGLE,
            width=22,
        )
        scrollbar.config(command=self.turn_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.turn_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for turn in self.turns:
            step = turn.get("step", "?")
            label = turn.get("label", "?")
            self.turn_listbox.insert(tk.END, f" {step:>2}. {label}")

        self.turn_listbox.bind("<<ListboxSelect>>", self._on_turn_selected)

        # --- Centre: map canvas (the main focal point) ---
        map_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(map_frame, weight=3)

        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=map_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Right: collapsible text side panel ---
        self.side_frame = ttk.Frame(self.main_paned, width=320)
        self.main_paned.add(self.side_frame, weight=1)

        self.side_text = tk.Text(
            self.side_frame,
            wrap=tk.WORD,
            font=("TkFixedFont", 9),
            state=tk.DISABLED,
            width=40,
        )
        side_scroll = ttk.Scrollbar(self.side_frame, command=self.side_text.yview)
        self.side_text.configure(yscrollcommand=side_scroll.set)
        side_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.side_text.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Side panel toggle
    # ------------------------------------------------------------------

    def _toggle_side_panel(self) -> None:
        if self._side_panel_visible:
            self.main_paned.forget(self.side_frame)
            self._side_panel_visible = False
            self.toggle_btn.configure(text="◁ Show Panel")
        else:
            self.main_paned.add(self.side_frame, weight=1)
            self._side_panel_visible = True
            self.toggle_btn.configure(text="Hide Panel ▷")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _prev_turn(self) -> None:
        if self.current_turn_idx > 0:
            self.current_turn_idx -= 1
            self._update_display()

    def _next_turn(self) -> None:
        if self.current_turn_idx < len(self.turns) - 1:
            self.current_turn_idx += 1
            self._update_display()

    def _on_turn_selected(self, event) -> None:
        selection = self.turn_listbox.curselection()
        if selection:
            self.current_turn_idx = selection[0]
            self._update_display()

    # ------------------------------------------------------------------
    # Display Update
    # ------------------------------------------------------------------

    def _update_display(self) -> None:
        """Refresh map and side panel for the current turn."""
        if not self.turns:
            self.turn_label_var.set("No turns loaded")
            return

        idx = self.current_turn_idx
        turn = self.turns[idx]

        # Update listbox selection
        self.turn_listbox.selection_clear(0, tk.END)
        self.turn_listbox.selection_set(idx)
        self.turn_listbox.see(idx)

        # Nav label & button states
        step = turn.get("step", "?")
        label = turn.get("label", "?")
        self.turn_label_var.set(f"Turn {step}: {label}")

        self.prev_btn.state(["!disabled"] if idx > 0 else ["disabled"])
        self.next_btn.state(
            ["!disabled"] if idx < len(self.turns) - 1 else ["disabled"]
        )

        self._update_map(turn)
        self._update_side_panel(turn)

    # ------------------------------------------------------------------
    # Map rendering (unified: base map + order overlays)
    # ------------------------------------------------------------------

    def _update_map(self, turn: dict) -> None:
        """Render the map with order overlays for this turn.

        Prefers the pre-rendered ``orders_view.png`` if present; falls
        back to ``board.jpeg``; finally falls back to live rendering.
        """
        self.ax.clear()

        # 1. Try pre-rendered order-overlay image (best experience)
        orders_view_path = turn.get("orders_view_path")
        if orders_view_path and Path(orders_view_path).exists():
            img = mpimg.imread(orders_view_path)
            self.ax.imshow(img)
            self.ax.set_axis_off()
            self.fig.tight_layout(pad=0.5)
            self.canvas.draw()
            return

        # 2. Try board.jpeg fallback
        board_path = turn.get("board_image_path")
        if board_path and Path(board_path).exists():
            img = mpimg.imread(board_path)
            self.ax.imshow(img)
            self.ax.set_axis_off()
            self.fig.tight_layout(pad=0.5)
            self.canvas.draw()
            return

        # 3. Live render if no images available
        self._render_map_live(turn)
        self.fig.tight_layout(pad=0.5)
        self.canvas.draw()

    def _render_map_live(self, turn: dict) -> None:
        """Render the map + orders directly onto self.ax using topology data."""
        ax = self.ax
        faces = self._faces
        borders_data = self._borders_data
        edges_data = self._edges_data
        vertex_coords = self._vertex_coords
        power_colors = self._power_colors

        terrain_colors = {
            "land": "#C5E0B4",
            "sea": "#BDD7EE",
            "impassable": "#A6A6A6",
        }

        # -- Province polygons --
        state_data = turn.get("state") or {}
        ownership = state_data.get("ownership", {})

        for face_id, face_data in faces.items():
            polygon = self._get_face_polygon(face_id)
            if not polygon or len(polygon) < 3:
                continue
            poly_arr = np.array(polygon)

            face_type = face_data.get("type", "land")
            owner = ownership.get(face_id, face_data.get("owner"))
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

            ax.fill(
                poly_arr[:, 0], poly_arr[:, 1],
                color=color, alpha=alpha, edgecolor="black", linewidth=0.4,
            )

        # -- SC markers --
        for face_id, face_data in faces.items():
            if face_data.get("is_supply_center", False):
                lp = face_data.get("label_positions", {})
                pos = lp.get("sc_position", face_data.get("center", [0.5, 0.5]))
                ax.plot(
                    pos[0], pos[1], "o",
                    markersize=6, color="gold",
                    markeredgecolor="black", markeredgewidth=1.2, zorder=8,
                )

        # -- Province names --
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
                ax.text(
                    tx, ty, name, ha="center", va="center",
                    fontsize=4.5, fontstyle="italic", color="#2B5797", zorder=4,
                )
            else:
                ax.text(
                    tx, ty, name, ha="center", va="center",
                    fontsize=4.5, fontweight="bold",
                    bbox=dict(
                        boxstyle="round,pad=0.12", facecolor="white",
                        alpha=0.6, edgecolor="none",
                    ),
                    zorder=5,
                )

        # -- Draw units from state --
        units = state_data.get("units", {})
        for loc, unit_data in units.items():
            face_data = faces.get(loc, {})
            lp = face_data.get("label_positions", {})
            pos = lp.get("unit_position", face_data.get("center"))
            if not pos:
                continue
            ut = unit_data.get("unit_type", "army")
            ut_char = "A" if ut == "army" else "F"
            power = unit_data.get("power")
            uc = power_colors.get(power, "#555555")
            marker = "o" if ut_char == "A" else "^"
            ax.plot(
                pos[0], pos[1], marker,
                markersize=11, color=uc,
                markeredgecolor="black", markeredgewidth=1.8, zorder=15,
            )
            ax.text(
                pos[0], pos[1] - (0.001 if ut_char == "F" else 0),
                ut_char, ha="center", va="center",
                fontsize=6, fontweight="bold", color="white", zorder=16,
            )

        # -- Draw order overlays --
        orders_data = turn.get("orders") or {}
        resolved = orders_data.get("resolved_orders", [])
        if resolved:
            try:
                from order_viewer import (
                    draw_orders, draw_legend, build_name_to_id_map,
                )
                name_to_id = build_name_to_id_map(faces)

                def _face_center(loc):
                    """Resolve a location name to its face center coords."""
                    fid = name_to_id.get(loc)
                    if fid is None:
                        return None
                    fd = faces.get(fid)
                    if fd is None:
                        return None
                    c = fd.get("center")
                    return (c[0], c[1]) if c else None

                def _unit_pos(loc):
                    """Get pre-determined unit position or fall back to center."""
                    fid = name_to_id.get(loc)
                    if fid is None:
                        return None
                    fd = faces.get(fid)
                    if fd is None:
                        return None
                    lp = fd.get("label_positions", {})
                    p = lp.get("unit_position")
                    if p:
                        return (p[0], p[1])
                    return _face_center(loc)

                draw_orders(
                    ax, resolved, _face_center, _unit_pos,
                    power_colors, name_to_id, faces,
                )
                draw_legend(ax, resolved, self._power_list, power_colors)
            except ImportError:
                pass  # order_viewer not available

        # -- Title --
        turn_label = orders_data.get("turn", turn.get("label", ""))
        ax.set_title(
            f"Diplomacy — {turn_label}",
            fontsize=13, fontweight="bold", pad=10,
        )
        ax.set_aspect("equal")
        ax.axis("off")

    def _get_face_polygon(self, face_id: str) -> list[list[float]]:
        """Reconstruct a face polygon from topology data."""
        face_data = self._faces.get(face_id, {})
        face_edges: list[str] = []
        for border_id in face_data.get("borders", []):
            if border_id in self._borders_data:
                face_edges.extend(self._borders_data[border_id].get("edges", []))

        if not face_edges:
            return []

        vertex_graph: dict[str, list[str]] = {}
        for edge_id in face_edges:
            if edge_id not in self._edges_data:
                continue
            edge = self._edges_data[edge_id]
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
            if current in self._vertex_coords:
                polygon.append(self._vertex_coords[current])
            next_v = None
            for nb in vertex_graph.get(current, []):
                if nb not in visited:
                    next_v = nb
                    break
            if next_v is None:
                break
            current = next_v

        return polygon

    # ------------------------------------------------------------------
    # Side panel (collapsible text: orders + summary)
    # ------------------------------------------------------------------

    def _update_side_panel(self, turn: dict) -> None:
        """Populate the side text panel with orders and summary."""
        self.side_text.configure(state=tk.NORMAL)
        self.side_text.delete("1.0", tk.END)

        # --- Orders section ---
        orders_data = turn.get("orders")
        if orders_data:
            turn_label = orders_data.get("turn", "?")
            self.side_text.insert(tk.END, f"═══ ORDERS: {turn_label} ═══\n\n")

            resolved = orders_data.get("resolved_orders", [])
            if resolved:
                by_power: dict[str, list[dict]] = {}
                for od in resolved:
                    power = od.get("power", "Unknown")
                    by_power.setdefault(power, []).append(od)

                for power in sorted(by_power):
                    self.side_text.insert(tk.END, f"  {power}:\n")
                    for od in by_power[power]:
                        line = self._format_order_line(od)
                        self.side_text.insert(tk.END, f"    {line}\n")
                    self.side_text.insert(tk.END, "\n")

            winter_log = orders_data.get("winter_log")
            if winter_log:
                self.side_text.insert(tk.END, "  Winter Adjustments:\n")
                for wl in winter_log.splitlines():
                    self.side_text.insert(tk.END, f"    {wl}\n")
                self.side_text.insert(tk.END, "\n")

            dislodged = orders_data.get("dislodged", {})
            if dislodged:
                self.side_text.insert(tk.END, "  Dislodged:\n")
                for loc, attacker in dislodged.items():
                    self.side_text.insert(tk.END, f"    {loc} (by {attacker})\n")
                self.side_text.insert(tk.END, "\n")

        # --- Summary section ---
        summary = turn.get("summary")
        if summary:
            self.side_text.insert(tk.END, "═══ TURN SUMMARY ═══\n\n")
            self.side_text.insert(tk.END, summary)

        self.side_text.configure(state=tk.DISABLED)

    @staticmethod
    def _format_order_line(od: dict) -> str:
        """Format a single order dict into a compact display string."""
        otype = od.get("order_type", "hold")
        ut = od.get("unit_type", "?")
        loc = od.get("location", "?")
        result = od.get("result", "pending")
        target = od.get("target", "")

        if otype == "move":
            return f"{ut} {loc} → {target}  [{result}]"
        elif otype == "support":
            s_from = od.get("support_from", "?")
            s_to = od.get("support_to", "")
            if s_to:
                return f"{ut} {loc} S {s_from} → {s_to}  [{result}]"
            return f"{ut} {loc} S {s_from} H  [{result}]"
        elif otype == "convoy":
            s_from = od.get("support_from", "?")
            return f"{ut} {loc} C {s_from} → {target}  [{result}]"
        elif otype == "build":
            return f"BUILD {ut} {loc}"
        elif otype == "disband":
            return f"DISBAND {ut} {loc}"
        return f"{ut} {loc} H  [{result}]"

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the tkinter main loop."""
        self.root.mainloop()


# ===================================================================
# CLI renderer (headless / non-interactive)
# ===================================================================

def print_game_summary(game_dir: str | Path) -> None:
    """Print a text-only game summary to stdout (no GUI required).

    Useful for CI, scripting, or quick inspection of a game directory.
    """
    data = load_game_output(game_dir)
    meta = data["metadata"]
    result = data["result"]
    turns = data["turns"]

    print("=" * 60)
    print("  DIPLOMACY GAME REPLAY")
    print("=" * 60)
    print(f"  Game directory: {data['game_dir']}")
    print(f"  Powers: {', '.join(sorted(meta.get('powers', {})))}")
    print(f"  Turns recorded: {len(turns)}")

    if result:
        winner = result.get("winner") or "No winner"
        print(f"  Winner: {winner}")
        print(f"  Turns played: {result.get('turns_played', '?')}")
        print("\n  Final supply-center counts:")
        for power, count in sorted(
            result.get("final_sc_counts", {}).items(), key=lambda x: -x[1]
        ):
            print(f"    {power:20s} : {count}")

    print("\n  Turn list:")
    for t in turns:
        step = t.get("step", "?")
        label = t.get("label", "?")
        has_img = "✓" if t.get("has_orders_view") or t.get("has_board_image") else "✗"
        print(f"    {step:>2}. {label:<20s}  [image: {has_img}]")

    print("=" * 60)


# ===================================================================
# CLI entry point
# ===================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diplomacy Game Viewer — replay and explore game output.",
    )
    parser.add_argument(
        "game_dir",
        help="Path to a game output directory (e.g. outputs/game_20260408_224500)",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Print a text-only summary instead of launching the GUI.",
    )
    args = parser.parse_args()

    if args.text:
        print_game_summary(args.game_dir)
        return

    if not _HAS_GUI:
        print(
            "ERROR: GUI libraries are not available. "
            "Use --text for a text-only summary, or install "
            "tkinter and matplotlib.",
            file=sys.stderr,
        )
        sys.exit(1)

    viewer = GameViewer(args.game_dir)
    viewer.run()


if __name__ == "__main__":
    main()
