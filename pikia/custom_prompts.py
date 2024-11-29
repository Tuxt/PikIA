from InquirerPy.prompts.checkbox import CheckboxPrompt
from typing import Any, Callable

class CheckboxPromptWithStatus(CheckboxPrompt):
    def __init__(self, initial_status: str, status_updater: Callable[[Any], Any], *args, **kwargs):
        kwargs['instruction'] = initial_status
        self.status_updater = status_updater
        super().__init__(*args, **kwargs)

    @property
    def instruction(self):
        return super().instruction

    @instruction.setter
    def instruction(self, value):
        self._instruction = value

    def _handle_toggle_choice(self, _) -> None:
        result = super()._handle_toggle_choice(_)
        self.instruction = self.status_updater(self.selected_choices)
        return result

    def _handle_toggle_all(self, _, value: bool | None = None) -> None:
        result = super()._handle_toggle_all(_, value)
        self.instruction = self.status_updater(self.selected_choices)
        return result
