from PyQt5.QtCore import pyqtSignal

from autocomplete_line_text_field import AutocompleteLineTextField


class EditLemmasTextField(AutocompleteLineTextField):
    """
    Text field that suggest autocompletions of lines and sends a signal when a colon is
    typed.
    """

    colonTyped = pyqtSignal()  # Custom signal emitted when a colon is typed

    def __init__(
        self,
        styling,
        position=None,
        styling_key=None,
        num_lines=None,
        unfocus_on_click=True,
        hide_scrollbar=True,
    ):
        super().__init__(
            styling, position, styling_key, num_lines, unfocus_on_click, hide_scrollbar
        )

    def keyPressEvent(self, event):
        if event.text() == ":":
            self.colonTyped.emit()
        super().keyPressEvent(event)
