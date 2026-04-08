#!/usr/bin/env python3
"""
Game Viewer — unified interface for replaying Diplomacy games.

Launch the viewer by pointing it at a game output directory produced by
the standardized export (see ``game/game_export.py``)::

    python game_viewer.py outputs/game_20260408_224500

The viewer displays:

* **Board image** for the selected turn (rendered live from map + state
  data when a JPEG is not available).
* **Orders** submitted and their resolution results.
* **Turn summary** (human-readable text).
* **Navigation controls** — Previous / Next buttons and a turn list
  to click through the game turn by turn.

The interface is built on tkinter + matplotlib (consistent with the
existing ``map_viewer.py``).
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
        self.result = self.game_data["result"]
        self.current_turn_idx = 0

        # ----- Root window -----
        self.root = tk.Tk()
        self.root.title(f"Diplomacy Game Viewer — {Path(game_dir).name}")
        self.root.geometry("1280x860")
        self.root.minsize(900, 600)

        self._build_ui()
        self._update_display()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Assemble all widgets."""
        # Top info bar
        info_frame = ttk.Frame(self.root, padding=5)
        info_frame.pack(fill=tk.X)

        powers_text = ", ".join(sorted(self.metadata.get("powers", {}).keys()))
        ttk.Label(
            info_frame,
            text=f"Powers: {powers_text}",
            font=("TkDefaultFont", 10),
        ).pack(side=tk.LEFT)

        if self.result:
            winner = self.result.get("winner") or "No winner"
            ttk.Label(
                info_frame,
                text=f"   |   Result: {winner}  ({self.result.get('turns_played', '?')} turns)",
                font=("TkDefaultFont", 10, "bold"),
            ).pack(side=tk.LEFT)

        # ----- Main paned window: left sidebar + right content -----
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Left: turn list ---
        left_frame = ttk.Frame(paned, width=220)
        paned.add(left_frame, weight=0)

        ttk.Label(left_frame, text="Turns", font=("TkDefaultFont", 11, "bold")).pack(
            pady=(0, 4)
        )

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.turn_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("TkFixedFont", 10),
            selectmode=tk.SINGLE,
        )
        scrollbar.config(command=self.turn_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.turn_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for turn in self.turns:
            step = turn.get("step", "?")
            label = turn.get("label", "?")
            self.turn_listbox.insert(tk.END, f" {step:>2}. {label}")

        self.turn_listbox.bind("<<ListboxSelect>>", self._on_turn_selected)

        # --- Right: content area ---
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        # Navigation buttons
        nav_frame = ttk.Frame(right_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 4))

        self.prev_btn = ttk.Button(nav_frame, text="◀ Previous", command=self._prev_turn)
        self.prev_btn.pack(side=tk.LEFT, padx=4)

        self.turn_label_var = tk.StringVar(value="")
        ttk.Label(
            nav_frame,
            textvariable=self.turn_label_var,
            font=("TkDefaultFont", 12, "bold"),
        ).pack(side=tk.LEFT, expand=True)

        self.next_btn = ttk.Button(nav_frame, text="Next ▶", command=self._next_turn)
        self.next_btn.pack(side=tk.RIGHT, padx=4)

        # ----- Content notebook (tabs: Board | Orders | Summary) -----
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Board image
        board_frame = ttk.Frame(self.notebook)
        self.notebook.add(board_frame, text="Board")

        self.fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=board_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Tab 2: Orders
        orders_frame = ttk.Frame(self.notebook)
        self.notebook.add(orders_frame, text="Orders")

        self.orders_text = tk.Text(
            orders_frame, wrap=tk.WORD, font=("TkFixedFont", 10), state=tk.DISABLED
        )
        orders_scroll = ttk.Scrollbar(orders_frame, command=self.orders_text.yview)
        self.orders_text.configure(yscrollcommand=orders_scroll.set)
        orders_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.orders_text.pack(fill=tk.BOTH, expand=True)

        # Tab 3: Summary
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="Summary")

        self.summary_text = tk.Text(
            summary_frame, wrap=tk.WORD, font=("TkFixedFont", 10), state=tk.DISABLED
        )
        summary_scroll = ttk.Scrollbar(summary_frame, command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.pack(fill=tk.BOTH, expand=True)

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
        """Refresh all panels to show the current turn."""
        if not self.turns:
            self.turn_label_var.set("No turns loaded")
            return

        idx = self.current_turn_idx
        turn = self.turns[idx]

        # Update listbox selection
        self.turn_listbox.selection_clear(0, tk.END)
        self.turn_listbox.selection_set(idx)
        self.turn_listbox.see(idx)

        # Update navigation label & button states
        step = turn.get("step", "?")
        label = turn.get("label", "?")
        self.turn_label_var.set(f"Turn {step}: {label}")

        self.prev_btn.state(["!disabled"] if idx > 0 else ["disabled"])
        self.next_btn.state(
            ["!disabled"] if idx < len(self.turns) - 1 else ["disabled"]
        )

        # --- Board tab ---
        self._update_board(turn)

        # --- Orders tab ---
        self._update_orders(turn)

        # --- Summary tab ---
        self._update_summary(turn)

    def _update_board(self, turn: dict) -> None:
        """Show the board image for this turn (from JPEG if available)."""
        self.ax.clear()
        board_path = turn.get("board_image_path")
        if board_path and Path(board_path).exists():
            img = mpimg.imread(board_path)
            self.ax.imshow(img)
            self.ax.set_axis_off()
        else:
            self.ax.text(
                0.5, 0.5,
                "No board image available for this turn.",
                ha="center", va="center",
                fontsize=12, color="gray",
                transform=self.ax.transAxes,
            )
            self.ax.set_axis_off()
        self.fig.tight_layout()
        self.canvas.draw()

    def _update_orders(self, turn: dict) -> None:
        """Populate the Orders tab."""
        self.orders_text.configure(state=tk.NORMAL)
        self.orders_text.delete("1.0", tk.END)

        orders_data = turn.get("orders")
        if orders_data is None:
            self.orders_text.insert(tk.END, "No order data available.\n")
        else:
            turn_label = orders_data.get("turn", "?")
            self.orders_text.insert(tk.END, f"Turn: {turn_label}\n")
            self.orders_text.insert(tk.END, "=" * 50 + "\n\n")

            resolved = orders_data.get("resolved_orders", [])
            if resolved:
                # Group by power
                by_power: dict[str, list[dict]] = {}
                for od in resolved:
                    power = od.get("power", "Unknown")
                    by_power.setdefault(power, []).append(od)

                for power in sorted(by_power):
                    self.orders_text.insert(tk.END, f"{power}:\n")
                    for od in by_power[power]:
                        otype = od.get("order_type", "hold")
                        ut = od.get("unit_type", "?")
                        loc = od.get("location", "?")
                        result = od.get("result", "pending")
                        target = od.get("target", "")
                        if otype == "move":
                            line = f"  {ut} {loc} → {target}  [{result}]"
                        elif otype == "support":
                            s_from = od.get("support_from", "?")
                            s_to = od.get("support_to", "")
                            if s_to:
                                line = f"  {ut} {loc} S {s_from} → {s_to}  [{result}]"
                            else:
                                line = f"  {ut} {loc} S {s_from} H  [{result}]"
                        elif otype == "convoy":
                            s_from = od.get("support_from", "?")
                            line = f"  {ut} {loc} C {s_from} → {target}  [{result}]"
                        elif otype == "build":
                            line = f"  BUILD {ut} {loc}"
                        elif otype == "disband":
                            line = f"  DISBAND {ut} {loc}"
                        else:
                            line = f"  {ut} {loc} H  [{result}]"
                        self.orders_text.insert(tk.END, line + "\n")
                    self.orders_text.insert(tk.END, "\n")
            else:
                self.orders_text.insert(tk.END, "(No orders for this turn)\n")

            # Winter log
            winter_log = orders_data.get("winter_log")
            if winter_log:
                self.orders_text.insert(tk.END, "\nWinter Adjustments:\n")
                self.orders_text.insert(tk.END, winter_log + "\n")

            # Dislodged
            dislodged = orders_data.get("dislodged", {})
            if dislodged:
                self.orders_text.insert(tk.END, "\nDislodged:\n")
                for loc, attacker in dislodged.items():
                    self.orders_text.insert(tk.END, f"  {loc} (by {attacker})\n")

        self.orders_text.configure(state=tk.DISABLED)

    def _update_summary(self, turn: dict) -> None:
        """Populate the Summary tab."""
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)

        summary = turn.get("summary")
        if summary:
            self.summary_text.insert(tk.END, summary)
        else:
            self.summary_text.insert(tk.END, "No summary available.\n")

        self.summary_text.configure(state=tk.DISABLED)

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
        has_img = "✓" if t.get("has_board_image") else "✗"
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
