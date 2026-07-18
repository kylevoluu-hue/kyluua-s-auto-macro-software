"""A single editable macro step, rendered as a row of controls."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..models import ActionType, Step
from . import choices

# Display labels for the action dropdown, and the reverse mapping.
ACTION_LABELS: dict[ActionType, str] = {
    ActionType.KEY: "Key tap",
    ActionType.HOTKEY: "Hotkey",
    ActionType.TEXT: "Type text",
    ActionType.DELAY: "Wait",
}
LABEL_TO_ACTION: dict[str, ActionType] = {v: k for k, v in ACTION_LABELS.items()}


def value_choices_for(action: ActionType) -> list[str]:
    """The dropdown options offered for a step's value, by action type."""

    if action is ActionType.KEY:
        return choices.KEY_CHOICES
    if action is ActionType.HOTKEY:
        return choices.COMBO_CHOICES
    if action is ActionType.DELAY:
        return choices.DELAY_CHOICES
    return []  # TEXT: free-form, no preset list


class StepRow(ctk.CTkFrame):
    """Editable widgets for one :class:`Step`.

    The row owns no persistent state beyond its widgets; call :meth:`collect`
    to read the current widget values back into a fresh :class:`Step`
    (preserving the original id).
    """

    def __init__(
        self,
        master,
        step: Step,
        *,
        on_change: Callable[[], None],
        on_delete: Callable[["StepRow"], None],
        on_move: Callable[["StepRow", int], None],
    ) -> None:
        super().__init__(master)
        self._step_id = step.id
        self._on_change = on_change
        self._on_delete = on_delete
        self._on_move = on_move

        self.grid_columnconfigure(2, weight=1)  # value widget stretches

        self.enabled_var = ctk.BooleanVar(value=step.enabled)
        self.action_var = ctk.StringVar(value=ACTION_LABELS[step.action])
        self.value_var = ctk.StringVar(value=step.value)
        self.delay_var = ctk.StringVar(value=str(step.delay_after_ms))
        self.repeat_var = ctk.StringVar(value=str(step.repeat))

        # Enable / disable this step.
        self.enable_chk = ctk.CTkCheckBox(
            self, text="", width=24, variable=self.enabled_var, command=self._changed
        )
        self.enable_chk.grid(row=0, column=0, padx=(8, 4), pady=6)

        # Action type.
        self.action_menu = ctk.CTkOptionMenu(
            self,
            width=104,
            values=list(ACTION_LABELS.values()),
            variable=self.action_var,
            command=self._on_action_change,
        )
        self.action_menu.grid(row=0, column=1, padx=4, pady=6)

        # Value — a selectable dropdown you can also type into (key name /
        # combo / preset delay), or a free text field for "Type text".
        self.value_combo = ctk.CTkComboBox(
            self,
            values=value_choices_for(step.action),
            variable=self.value_var,
            command=lambda _v: self._changed(),
        )
        self.value_combo.grid(row=0, column=2, padx=4, pady=6, sticky="ew")
        self.value_var.trace_add("write", lambda *_: self._changed())

        # Delay after (ms).
        ctk.CTkLabel(self, text="delay").grid(row=0, column=3, padx=(8, 0))
        self.delay_entry = ctk.CTkEntry(self, width=60, textvariable=self.delay_var)
        self.delay_entry.grid(row=0, column=4, padx=4, pady=6)
        self.delay_var.trace_add("write", lambda *_: self._changed())

        # Repeat count.
        ctk.CTkLabel(self, text="×").grid(row=0, column=5, padx=(8, 0))
        self.repeat_entry = ctk.CTkEntry(self, width=44, textvariable=self.repeat_var)
        self.repeat_entry.grid(row=0, column=6, padx=4, pady=6)
        self.repeat_var.trace_add("write", lambda *_: self._changed())

        # Reorder + delete controls.
        self.up_btn = ctk.CTkButton(
            self, text="▲", width=28, command=lambda: self._on_move(self, -1)
        )
        self.up_btn.grid(row=0, column=7, padx=(8, 2), pady=6)
        self.down_btn = ctk.CTkButton(
            self, text="▼", width=28, command=lambda: self._on_move(self, 1)
        )
        self.down_btn.grid(row=0, column=8, padx=2, pady=6)
        self.del_btn = ctk.CTkButton(
            self,
            text="✕",
            width=28,
            fg_color="#a83232",
            hover_color="#c0392b",
            command=lambda: self._on_delete(self),
        )
        self.del_btn.grid(row=0, column=9, padx=(2, 8), pady=6)

        self._sync_repeat_state(step.action)

    # -- callbacks ---------------------------------------------------------

    def _changed(self) -> None:
        self._on_change()

    def _on_action_change(self, label: str) -> None:
        action = LABEL_TO_ACTION.get(label, ActionType.KEY)
        self.value_combo.configure(values=value_choices_for(action))
        self._sync_repeat_state(action)
        self._changed()

    def _sync_repeat_state(self, action: ActionType) -> None:
        """Repeat makes no sense for a Wait step; disable it there."""

        state = "disabled" if action is ActionType.DELAY else "normal"
        self.repeat_entry.configure(state=state)

    # -- data --------------------------------------------------------------

    @property
    def action(self) -> ActionType:
        return LABEL_TO_ACTION.get(self.action_var.get(), ActionType.KEY)

    @staticmethod
    def _safe_int(text: str, default: int, minimum: int) -> int:
        try:
            return max(minimum, int(float(text)))
        except (TypeError, ValueError):
            return default

    def collect(self) -> Step:
        """Read the current widget values into a new :class:`Step`."""

        return Step(
            action=self.action,
            value=self.value_var.get(),
            delay_after_ms=self._safe_int(self.delay_var.get(), 0, 0),
            repeat=self._safe_int(self.repeat_var.get(), 1, 1),
            enabled=bool(self.enabled_var.get()),
            id=self._step_id,
        )
