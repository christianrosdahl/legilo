from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
from PyQt5.QtCore import Qt

from text_field import TextField


class AutocompleteLineTextField(TextField):
    """Text field that suggest autocompletions of lines"""

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
        self.suggestions = set()
        self.current_suggestion = ""
        self.block_updates = True  # Flag to prevent recursion
        self.textChanged.connect(self.update_suggestion)

    def edit(self):
        super().edit()
        self.block_updates = False
        self.update_suggestion()

    def stop_edit(self):
        super().stop_edit()
        self.block_updates = True

    def set_suggestions(self, suggestions):
        self.suggestions = suggestions

    def update_suggestion(self):
        if self.block_updates:
            return

        self.block_updates = True  # Prevent recursion

        self.remove_suggestion()

        cursor = self.textCursor()
        original_position = cursor.position()

        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        line_before_cursor = cursor.selectedText()
        cursor.setPosition(original_position)

        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        line_after_cursor = cursor.selectedText()
        cursor.setPosition(original_position)

        if len(line_before_cursor) == 0 or not len(line_after_cursor) == 0:
            self.block_updates = False  # Re-enable updates
            return

        self.setTextCursor(cursor)

        # Find a matching suggestion
        matching = next(
            (s for s in self.suggestions if s.startswith(line_before_cursor)), ""
        )
        if matching:
            self.insert_suggestion(matching[len(line_before_cursor) :])

        self.block_updates = False  # Re-enable updates

    def insert_suggestion(self, suggestion):
        if not suggestion:
            return

        self.current_suggestion = suggestion
        cursor = self.textCursor()
        cursor.beginEditBlock()

        # Save current cursor position
        original_position = cursor.position()

        # Insert the suggestion text styled in gray
        format_ = QTextCharFormat()
        format_.setForeground(QColor(self.styling["colors"]["text_autocomplete_color"]))
        cursor.insertText(self.current_suggestion, format_)

        # Restore the original cursor position
        cursor.setPosition(original_position)
        self.setTextCursor(cursor)

        cursor.endEditBlock()

    def remove_suggestion(self):
        if not self.current_suggestion:
            return

        self.block_updates = True  # Prevent recursion

        cursor = self.textCursor()
        cursor.beginEditBlock()

        # Remove the light gray suggestion
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()

        cursor.endEditBlock()
        self.current_suggestion = ""

        self.block_updates = False  # Re-enable updates

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab and self.current_suggestion:
            accepted_suggestion = self.current_suggestion
            self.remove_suggestion()
            # Accept the current suggestion
            cursor = self.textCursor()
            cursor.insertText(accepted_suggestion)
            self.current_suggestion = ""
        else:
            self.remove_suggestion()
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.remove_suggestion()
        super().mousePressEvent(event)
