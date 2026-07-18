"""The main AutoMacro application window (customtkinter)."""

from __future__ import annotations

import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .. import APP_NAME, __version__
from ..backends import create_input_backend, create_window_backend
from ..config import load_config, save_config
from ..engine import EngineListener, MacroEngine
from ..hotkeys import create_hotkey_manager
from ..keyspec import KeySpecError, is_valid_key, parse_hotkey
from ..models import ActionType, AppConfig, Macro, MatchMode, Step
from . import choices
from .step_row import StepRow

# Label <-> enum maps for the match-mode dropdown.
MATCH_LABELS: dict[MatchMode, str] = {
    MatchMode.CONTAINS: "Contains",
    MatchMode.EXACT: "Exact",
    MatchMode.STARTS_WITH: "Starts with",
    MatchMode.REGEX: "Regex",
}
MATCH_LABELS_INV = {v: k for k, v in MATCH_LABELS.items()}

THEME_OPTIONS = ["System", "Dark", "Light"]


def _safe_int(text: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(float(text)))
    except (TypeError, ValueError):
        return default


def _asset(name: str) -> Path | None:
    """Locate a bundled asset both in source and inside a PyInstaller bundle."""

    base = getattr(sys, "_MEIPASS", None)
    candidates = []
    if base:
        candidates.append(Path(base) / "assets" / name)
    candidates.append(Path(__file__).resolve().parents[3] / "assets" / name)
    for path in candidates:
        if path.exists():
            return path
    return None


class _UiEngineListener(EngineListener):
    """Marshals engine callbacks (worker thread) onto the Tk main thread."""

    def __init__(self, window: "AppWindow") -> None:
        self._win = window

    def state_changed(self, running: bool) -> None:
        self._win.after(0, self._win._on_engine_state, running)

    def status(self, message: str) -> None:
        self._win.after(0, self._win._on_engine_status, message)

    def loop_completed(self, completed: int, total: int) -> None:
        self._win.after(0, self._win._on_engine_loop, completed, total)

    def error(self, message: str) -> None:
        self._win.after(0, self._win._on_engine_error, message)


class AppWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.config_model: AppConfig = load_config()
        ctk.set_appearance_mode(self.config_model.theme)
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} {__version__}")
        self.geometry("1040x740")
        self.minsize(940, 660)

        # Backends + engine + global hotkeys.
        self.input_backend = create_input_backend()
        self.window_backend = create_window_backend()
        self.hotkeys = create_hotkey_manager()
        self.engine = MacroEngine(
            self.input_backend,
            self.window_backend,
            listener=_UiEngineListener(self),
            reactivate_each_loop=self.config_model.reactivate_each_loop,
        )

        self._running = False
        self._running_macro: Macro | None = None
        self._autosave_job = None
        self.step_rows: list[StepRow] = []

        self.title_font = ctk.CTkFont(size=20, weight="bold")
        self.section_font = ctk.CTkFont(size=14, weight="bold")

        self._build_layout()
        self._set_icon()

        if not self.config_model.macros:
            self.config_model.macros.append(Macro())
        self.current_macro = self.config_model.active_macro()
        self._rebuild_sidebar()
        self._load_macro_into_form()
        self._apply_hotkeys()
        self._report_backend_health()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- layout ------------------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_editor()
        self._build_footer()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=f"⌨  {APP_NAME}", font=self.title_font).grid(
            row=0, column=0, sticky="w", padx=16, pady=12
        )
        ctk.CTkLabel(header, text="Theme").grid(row=0, column=1, padx=(0, 6))
        self.theme_menu = ctk.CTkOptionMenu(
            header,
            width=110,
            values=THEME_OPTIONS,
            command=self._on_theme_change,
        )
        self.theme_menu.set(self.config_model.theme.capitalize())
        self.theme_menu.grid(row=0, column=2, padx=(0, 16), pady=12)

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="nsw")
        sidebar.grid_rowconfigure(1, weight=1)
        # Constrain children to the sidebar's width so the button bar cannot
        # overflow and slide under the editor (the previous overlap bug).
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="Macros", font=self.section_font).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 6)
        )
        self.macro_list = ctk.CTkScrollableFrame(sidebar)
        self.macro_list.grid(row=1, column=0, sticky="nsew", padx=8)
        self.macro_list.grid_columnconfigure(0, weight=1)

        btn_bar = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_bar.grid(row=2, column=0, sticky="ew", padx=8, pady=10)
        btn_bar.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            btn_bar, text="＋ New", width=96, command=self._new_macro
        ).grid(row=0, column=0, padx=(0, 3), pady=(0, 6), sticky="ew")
        ctk.CTkButton(
            btn_bar, text="⧉ Duplicate", width=96, command=self._duplicate_macro
        ).grid(row=0, column=1, padx=(3, 0), pady=(0, 6), sticky="ew")
        ctk.CTkButton(
            btn_bar,
            text="🗑  Delete macro",
            fg_color="#a83232",
            hover_color="#c0392b",
            command=self._delete_macro,
        ).grid(row=1, column=0, columnspan=2, sticky="ew")

    def _build_editor(self) -> None:
        editor = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        editor.grid(row=1, column=1, sticky="nsew", padx=12, pady=8)
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(3, weight=1)

        # --- Name ---------------------------------------------------------
        name_row = ctk.CTkFrame(editor, fg_color="transparent")
        name_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        name_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(name_row, text="Macro name", font=self.section_font).grid(
            row=0, column=0, padx=(0, 10)
        )
        self.name_var = ctk.StringVar()
        name_entry = ctk.CTkEntry(name_row, textvariable=self.name_var)
        name_entry.grid(row=0, column=1, sticky="ew")
        self.name_var.trace_add("write", lambda *_: self._on_field_change(sidebar=True))

        # --- Target app ---------------------------------------------------
        self._build_target_panel(editor)

        # --- Steps --------------------------------------------------------
        steps_bar = ctk.CTkFrame(editor, fg_color="transparent")
        steps_bar.grid(row=2, column=0, sticky="ew", pady=(10, 2))
        steps_bar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(steps_bar, text="Steps", font=self.section_font).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(steps_bar, text="＋ Add step", width=110, command=self._add_step).grid(
            row=0, column=1, sticky="e"
        )
        self.steps_container = ctk.CTkScrollableFrame(
            editor, label_text="Sequence (runs top to bottom)"
        )
        self.steps_container.grid(row=3, column=0, sticky="nsew")
        self.steps_container.grid_columnconfigure(0, weight=1)

        # --- Timing / cooldowns ------------------------------------------
        self._build_timing_panel(editor)

    def _build_target_panel(self, editor) -> None:
        panel = ctk.CTkFrame(editor)
        panel.grid(row=1, column=0, sticky="ew")
        panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(panel, text="Target app", font=self.section_font).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )

        self.target_var = ctk.StringVar()
        self.target_combo = ctk.CTkComboBox(
            panel, values=[], variable=self.target_var, command=lambda _: self._on_field_change()
        )
        self.target_combo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12)
        self.target_var.trace_add("write", lambda *_: self._on_field_change())

        ctk.CTkButton(panel, text="⟳ Refresh", width=100, command=self._refresh_windows).grid(
            row=1, column=2, padx=(6, 12)
        )

        controls = ctk.CTkFrame(panel, fg_color="transparent")
        controls.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=8)

        ctk.CTkLabel(controls, text="Match").grid(row=0, column=0, padx=(4, 4))
        self.match_var = ctk.StringVar(value=MATCH_LABELS[MatchMode.CONTAINS])
        ctk.CTkOptionMenu(
            controls,
            width=120,
            values=list(MATCH_LABELS.values()),
            variable=self.match_var,
            command=lambda _: self._on_field_change(),
        ).grid(row=0, column=1, padx=(0, 12))

        self.activate_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            controls,
            text="Focus target before running",
            variable=self.activate_var,
            command=self._on_field_change,
        ).grid(row=0, column=2, padx=8)

        self.focus_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            controls,
            text="Only while target is focused",
            variable=self.focus_var,
            command=self._on_field_change,
        ).grid(row=0, column=3, padx=8)

        hint = (
            "Empty target = send to whatever window is focused. "
            "Pick an open window from the list or type part of its title."
        )
        ctk.CTkLabel(panel, text=hint, text_color=("gray40", "gray60")).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10)
        )

    def _build_timing_panel(self, editor) -> None:
        panel = ctk.CTkFrame(editor)
        panel.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        for col in range(4):
            panel.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(panel, text="Cooldowns & timing", font=self.section_font).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 6)
        )

        self.start_delay_var = ctk.StringVar()
        self.cooldown_var = ctk.StringVar()
        self.loops_var = ctk.StringVar()
        self.jitter_var = ctk.DoubleVar(value=0.0)

        self._labeled_entry(panel, "Start delay (ms)", self.start_delay_var, 1, 0)
        self._labeled_entry(panel, "Loop cooldown (ms)", self.cooldown_var, 1, 1)
        self._labeled_entry(panel, "Loops (0 = ∞)", self.loops_var, 1, 2)

        jitter_box = ctk.CTkFrame(panel, fg_color="transparent")
        jitter_box.grid(row=1, column=3, sticky="ew", padx=8, pady=(0, 8))
        jitter_box.grid_columnconfigure(0, weight=1)
        self.jitter_label = ctk.CTkLabel(jitter_box, text="Timing jitter: 0%")
        self.jitter_label.grid(row=0, column=0, sticky="w")
        ctk.CTkSlider(
            jitter_box,
            from_=0.0,
            to=0.5,
            number_of_steps=50,
            variable=self.jitter_var,
            command=self._on_jitter_change,
        ).grid(row=1, column=0, sticky="ew")

        # Trigger + panic hotkeys — pick from a list, no typing required.
        trig = ctk.CTkFrame(panel, fg_color="transparent")
        trig.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=(2, 10))
        trig.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(trig, text="Start/stop hotkey").grid(row=0, column=0, padx=(4, 6))
        self.trigger_var = ctk.StringVar(value="f6")
        self.trigger_menu = ctk.CTkOptionMenu(
            trig,
            variable=self.trigger_var,
            values=choices.TRIGGER_CHOICES,
            command=lambda _v: self._apply_hotkeys(),
        )
        self.trigger_menu.grid(row=0, column=1, sticky="ew", padx=(0, 14))

        ctk.CTkLabel(trig, text="Emergency stop").grid(row=0, column=2, padx=(4, 6))
        self.panic_var = ctk.StringVar(value=self.config_model.panic_hotkey)
        self.panic_menu = ctk.CTkOptionMenu(
            trig,
            variable=self.panic_var,
            values=choices.with_current(
                self.config_model.panic_hotkey, choices.TRIGGER_CHOICES
            ),
            command=lambda _v: self._apply_hotkeys(),
        )
        self.panic_menu.grid(row=0, column=3, sticky="ew")

    def _labeled_entry(self, parent, label, var, row, col) -> None:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=col, sticky="ew", padx=8, pady=(0, 8))
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text=label).grid(row=0, column=0, sticky="w")
        entry = ctk.CTkEntry(box, textvariable=var)
        entry.grid(row=1, column=0, sticky="ew")
        var.trace_add("write", lambda *_: self._on_field_change())

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self.status_var = ctk.StringVar(value="Ready.")
        ctk.CTkLabel(footer, textvariable=self.status_var, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=12
        )
        self.run_button = ctk.CTkButton(
            footer,
            text="▶  Start",
            width=150,
            height=40,
            font=self.section_font,
            command=self._on_start,
        )
        self.run_button.grid(row=0, column=1, padx=(8, 6), pady=10)
        self.stop_button = ctk.CTkButton(
            footer,
            text="■  Stop",
            width=130,
            height=40,
            font=self.section_font,
            fg_color="#a83232",
            hover_color="#c0392b",
            command=self._on_stop,
            state="disabled",
        )
        self.stop_button.grid(row=0, column=2, padx=(6, 16), pady=10)

    # -- macro list / selection -------------------------------------------

    def _rebuild_sidebar(self) -> None:
        for child in self.macro_list.winfo_children():
            child.destroy()
        active_id = self.current_macro.id if getattr(self, "current_macro", None) else None
        for i, macro in enumerate(self.config_model.macros):
            selected = macro.id == active_id
            btn = ctk.CTkButton(
                self.macro_list,
                text=macro.name or "(unnamed)",
                anchor="w",
                fg_color=("gray75", "gray25") if selected else "transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda mid=macro.id: self._select_macro(mid),
            )
            btn.grid(row=i, column=0, sticky="ew", pady=2)

    def _select_macro(self, macro_id: str) -> None:
        if self._running:
            self._set_status("Stop the running macro before switching.", warn=True)
            return
        self._collect_into_macro()
        target = self.config_model.get_macro(macro_id)
        if target is None:
            return
        self.current_macro = target
        self.config_model.active_macro_id = macro_id
        self._load_macro_into_form()
        self._rebuild_sidebar()
        self._apply_hotkeys()
        self._autosave()

    def _new_macro(self) -> None:
        self._collect_into_macro()
        macro = Macro(name=f"Macro {len(self.config_model.macros) + 1}")
        self.config_model.macros.append(macro)
        self._select_macro(macro.id)

    def _duplicate_macro(self) -> None:
        if not self.current_macro:
            return
        self._collect_into_macro()
        data = self.current_macro.to_dict()
        clone = Macro.from_dict(data)
        clone.id = Macro().id  # fresh id
        for step in clone.steps:
            step.id = Step().id
        clone.name = f"{self.current_macro.name} (copy)"
        self.config_model.macros.append(clone)
        self._select_macro(clone.id)

    def _delete_macro(self) -> None:
        if self._running:
            self._set_status("Stop the running macro first.", warn=True)
            return
        if not self.current_macro:
            return
        if not messagebox.askyesno(
            "Delete macro", f"Delete '{self.current_macro.name}'?", parent=self
        ):
            return
        self.config_model.macros = [
            m for m in self.config_model.macros if m.id != self.current_macro.id
        ]
        if not self.config_model.macros:
            self.config_model.macros.append(Macro())
        self.current_macro = self.config_model.macros[0]
        self.config_model.active_macro_id = self.current_macro.id
        self._load_macro_into_form()
        self._rebuild_sidebar()
        self._autosave()

    # -- form load / collect ----------------------------------------------

    def _load_macro_into_form(self) -> None:
        m = self.current_macro
        if m is None:
            return
        self.name_var.set(m.name)
        self.target_var.set(m.target_window)
        self.match_var.set(MATCH_LABELS.get(m.match_mode, "Contains"))
        self.activate_var.set(m.activate_target)
        self.focus_var.set(m.require_focus)
        self.start_delay_var.set(str(m.start_delay_ms))
        self.cooldown_var.set(str(m.loop_cooldown_ms))
        self.loops_var.set(str(m.loops))
        self.jitter_var.set(m.jitter_pct)
        self._on_jitter_change(m.jitter_pct)
        self.trigger_menu.configure(
            values=choices.with_current(m.trigger_hotkey, choices.TRIGGER_CHOICES)
        )
        self.trigger_var.set(m.trigger_hotkey)
        self._rebuild_steps(m.steps)

    def _collect_into_macro(self) -> None:
        m = getattr(self, "current_macro", None)
        if m is None:
            return
        m.name = self.name_var.get().strip() or "Untitled"
        m.target_window = self.target_var.get().strip()
        m.match_mode = MATCH_LABELS_INV.get(self.match_var.get(), MatchMode.CONTAINS)
        m.activate_target = bool(self.activate_var.get())
        m.require_focus = bool(self.focus_var.get())
        m.start_delay_ms = _safe_int(self.start_delay_var.get(), 500, 0)
        m.loop_cooldown_ms = _safe_int(self.cooldown_var.get(), 1000, 0)
        m.loops = _safe_int(self.loops_var.get(), 1, 0)
        m.jitter_pct = round(float(self.jitter_var.get()), 3)
        m.trigger_hotkey = self.trigger_var.get().strip() or "f6"
        self.config_model.panic_hotkey = self.panic_var.get().strip() or "esc"
        if not self._running:
            m.steps = [row.collect() for row in self.step_rows]

    # -- steps -------------------------------------------------------------

    def _rebuild_steps(self, steps: list[Step]) -> None:
        for row in self.step_rows:
            row.destroy()
        self.step_rows = []
        for step in steps:
            self._append_step_row(step)
        self._regrid_steps()

    def _append_step_row(self, step: Step) -> StepRow:
        row = StepRow(
            self.steps_container,
            step,
            on_change=self._on_field_change,
            on_delete=self._delete_step,
            on_move=self._move_step,
        )
        self.step_rows.append(row)
        return row

    def _add_step(self) -> None:
        self._append_step_row(Step(action=ActionType.KEY, value=""))
        self._regrid_steps()
        self._on_field_change()

    def _delete_step(self, row: StepRow) -> None:
        if row in self.step_rows:
            self.step_rows.remove(row)
        row.destroy()
        self._regrid_steps()
        self._on_field_change()

    def _move_step(self, row: StepRow, delta: int) -> None:
        idx = self.step_rows.index(row)
        new_idx = idx + delta
        if 0 <= new_idx < len(self.step_rows):
            self.step_rows[idx], self.step_rows[new_idx] = (
                self.step_rows[new_idx],
                self.step_rows[idx],
            )
            self._regrid_steps()
            self._on_field_change()

    def _regrid_steps(self) -> None:
        for i, row in enumerate(self.step_rows):
            row.grid(row=i, column=0, sticky="ew", pady=3, padx=2)
        if not self.step_rows:
            # A gentle hint when the sequence is empty.
            pass

    # -- windows / target --------------------------------------------------

    def _refresh_windows(self) -> None:
        try:
            windows = self.window_backend.list_windows()
        except Exception as exc:
            self._set_status(f"Could not list windows: {exc}", warn=True)
            return
        titles = []
        seen = set()
        for w in windows:
            if w.title and w.title not in seen:
                seen.add(w.title)
                titles.append(w.title)
        self.target_combo.configure(values=titles)
        if not titles:
            self._set_status(
                "No windows found (targeting may be unavailable on this system).",
                warn=True,
            )
        else:
            self._set_status(f"Found {len(titles)} open window(s).")

    # -- change handling / autosave ---------------------------------------

    def _on_field_change(self, sidebar: bool = False) -> None:
        if sidebar:
            self._refresh_sidebar_labels()
        self._schedule_autosave()

    def _refresh_sidebar_labels(self) -> None:
        # Keep the sidebar button label in sync with the name field live.
        if not self.current_macro:
            return
        self.current_macro.name = self.name_var.get().strip() or "Untitled"
        self._rebuild_sidebar()

    def _on_jitter_change(self, value) -> None:
        pct = round(float(value) * 100)
        self.jitter_label.configure(text=f"Timing jitter: {pct}%")
        self._schedule_autosave()

    def _on_theme_change(self, value: str) -> None:
        ctk.set_appearance_mode(value.lower())
        self.config_model.theme = value.lower()
        self._schedule_autosave()

    def _schedule_autosave(self) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(700, self._autosave)

    def _autosave(self) -> None:
        self._autosave_job = None
        try:
            self._collect_into_macro()
            save_config(self.config_model)
        except Exception:
            pass  # never let a save error interrupt the UI

    # -- hotkeys -----------------------------------------------------------

    def _apply_hotkeys(self) -> None:
        if not getattr(self.hotkeys, "available", False):
            return
        trigger = (self.trigger_var.get() if hasattr(self, "trigger_var") else "f6").strip()
        panic = (self.panic_var.get() if hasattr(self, "panic_var") else "esc").strip()
        bindings = {}
        if panic:
            bindings[panic] = lambda: self.after(0, self._hotkey_stop)
        if trigger and trigger != panic:
            bindings[trigger] = lambda: self.after(0, self._hotkey_toggle)
        try:
            self.hotkeys.set_bindings(bindings)
        except Exception as exc:
            # A failure to register global hotkeys must never crash the app;
            # the on-screen Start/Stop button still works.
            self._set_status(f"Could not register global hotkeys: {exc}", warn=True)
            return
        self._schedule_autosave()
        if getattr(self.hotkeys, "errors", None):
            self._set_status("; ".join(self.hotkeys.errors), warn=True)

    def _hotkey_toggle(self) -> None:
        self._on_toggle()

    def _hotkey_stop(self) -> None:
        if self._running:
            self.engine.stop()

    # -- run control -------------------------------------------------------

    def _validate_macro(self, macro: Macro) -> list[str]:
        errors: list[str] = []
        if not macro.enabled_steps():
            errors.append("Add at least one enabled step.")
        for i, step in enumerate(macro.steps, start=1):
            if not step.enabled:
                continue
            if step.action is ActionType.HOTKEY:
                try:
                    parse_hotkey(step.value)
                except KeySpecError as exc:
                    errors.append(f"Step {i}: {exc}")
            elif step.action is ActionType.KEY:
                if not is_valid_key(step.value):
                    errors.append(f"Step {i}: '{step.value}' is not a valid key.")
            elif step.action is ActionType.DELAY:
                try:
                    if int(float(step.value)) < 0:
                        errors.append(f"Step {i}: wait must be >= 0 ms.")
                except (TypeError, ValueError):
                    errors.append(f"Step {i}: wait needs a number of milliseconds.")
        return errors

    def _on_start(self) -> None:
        if self._running:
            return
        if not self.input_backend.available:
            messagebox.showerror(
                APP_NAME,
                "Keyboard input is unavailable on this system, so macros cannot "
                "run.\n\nInstall the 'pynput' dependency and ensure a desktop "
                "session is available.",
                parent=self,
            )
            return
        self._collect_into_macro()
        macro = self.current_macro
        if macro is None:
            return
        errors = self._validate_macro(macro)
        if errors:
            messagebox.showerror(APP_NAME, "Please fix:\n\n• " + "\n• ".join(errors), parent=self)
            return
        self._running_macro = macro
        if self.engine.start(macro):
            self._set_running_ui(True)

    def _on_stop(self) -> None:
        if self.engine.is_running:
            self.engine.stop()

    def _on_toggle(self) -> None:
        """Start if idle, stop if running — used by the global hotkey."""

        if self._running:
            self._on_stop()
        else:
            self._on_start()

    def _set_running_ui(self, running: bool) -> None:
        self._running = running
        self.run_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    # -- engine callbacks (main thread) -----------------------------------

    def _on_engine_state(self, running: bool) -> None:
        self._set_running_ui(running)
        if not running and self.status_var.get().startswith("Running"):
            self._set_status("Stopped.")

    def _on_engine_status(self, message: str) -> None:
        self._set_status(message)

    def _on_engine_loop(self, completed: int, total: int) -> None:
        suffix = f"/{total}" if total else ""
        self._set_status(f"Completed loop {completed}{suffix}.")

    def _on_engine_error(self, message: str) -> None:
        self._set_status(message, warn=True)
        self._set_running_ui(False)

    def _set_status(self, message: str, warn: bool = False) -> None:
        self.status_var.set(message)

    # -- misc --------------------------------------------------------------

    def _report_backend_health(self) -> None:
        notes = []
        if not self.input_backend.available:
            notes.append("keyboard input unavailable")
        if not getattr(self.window_backend, "available", False):
            notes.append("window targeting unavailable (keys go to focused app)")
        if not getattr(self.hotkeys, "available", False):
            notes.append("global hotkeys unavailable")
        trigger = self.current_macro.trigger_hotkey if self.current_macro else "f6"
        if notes:
            self._set_status("Ready — note: " + "; ".join(notes) + ".")
        else:
            self._set_status(f"Ready. Press {trigger} to start/stop from any app.")

    def _set_icon(self) -> None:
        try:
            ico = _asset("icon.ico")
            if ico and sys.platform.startswith("win"):
                self.iconbitmap(str(ico))
                return
            png = _asset("icon.png")
            if png:
                import tkinter as tk

                self.iconphoto(True, tk.PhotoImage(file=str(png)))
        except Exception:
            pass  # a missing icon is not fatal

    def _on_close(self) -> None:
        try:
            self.engine.stop(wait=True, timeout=2)
        except Exception:
            pass
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        try:
            self._collect_into_macro()
            save_config(self.config_model)
        except Exception:
            pass
        self.destroy()


def run_app() -> int:
    app = AppWindow()
    app.mainloop()
    return 0
