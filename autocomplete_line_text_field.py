import requests

from PyQt5.QtGui import QInputMethodEvent, QTextCursor, QTextCharFormat, QColor
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
        use_wiktionary=False,
    ):
        super().__init__(
            styling, position, styling_key, num_lines, unfocus_on_click, hide_scrollbar
        )
        self.use_wiktionary = use_wiktionary
        self.suggestions = set()
        self.current_suggestion = ""
        self.block_updates = True  # Flag to prevent recursion
        self.is_dead_key_active = False
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

    def update_suggestion(self, get_from_wiktionary=False):
        if self.block_updates or self.is_dead_key_active:
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

        if self.use_wiktionary and get_from_wiktionary and len(line_before_cursor) > 0:
            self.add_wiktionary_suggestion(line_before_cursor)

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
        if event.key() == Qt.Key_Tab:
            if self.current_suggestion:
                accepted_suggestion = self.current_suggestion
                self.remove_suggestion()
                # Accept the current suggestion
                cursor = self.textCursor()
                cursor.insertText(accepted_suggestion)
                self.current_suggestion = ""
            else:
                self.remove_suggestion()
                self.update_suggestion(get_from_wiktionary=True)
        else:
            self.remove_suggestion()
            super().keyPressEvent(event)

    def inputMethodEvent(self, event: QInputMethodEvent):
        # Detect if the input event corresponds to a dead key
        if event.commitString() == "" and event.preeditString() != "":
            self.is_dead_key_active = True
            self.remove_suggestion()
        else:
            self.is_dead_key_active = False
        super().inputMethodEvent(event)

    def mousePressEvent(self, event):
        self.remove_suggestion()
        super().mousePressEvent(event)

    def add_wiktionary_suggestion(self, text):
        wiktionary_suggestion = self.get_wiktionary_suggestion(text)
        if not wiktionary_suggestion:
            return
        if not any(suggestion.startswith(text) for suggestion in self.suggestions):
            self.suggestions.add(wiktionary_suggestion)

    def get_wiktionary_suggestion(self, text):
        """
        Return the first found Wiktionary title starting with but not equal to `text`
        """
        url = "https://en.wiktionary.org/w/api.php"
        params = {
            "action": "query",
            "list": "allpages",
            "apprefix": text,  # Pages starting with 'text'
            "aplimit": 2,  # Limit the number of results
            "format": "json",
        }
        response = requests.get(url, params=params).json()
        titles = [
            page["title"]
            for page in response["query"]["allpages"]
            if page["title"] != text
        ]
        if len(titles) > 0:
            return titles[0]
        return None
