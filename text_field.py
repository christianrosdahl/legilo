from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QTextEdit


class TextField(QTextEdit):
    """Text field that doesn't get focused when clicked, unless explicitly set"""

    def __init__(
        self,
        styling,
        position=None,
        styling_key=None,
        num_lines=None,
        unfocus_on_click=True,
    ):
        super().__init__()
        self.styling = styling

        if position == "left":
            self.setMaximumWidth(self.styling["main_text_max_width"])
        elif position == "right":
            self.setMaximumWidth(self.styling["side_field_max_width"])

        self.setReadOnly(True)
        self.viewport().setCursor(Qt.ArrowCursor)
        self.setStyleSheet(self.styleSheet() + "QTextEdit { border: none; }")
        self.setStyleSheet(
            self.styleSheet()
            + "QTextEdit { padding:"
            + str(self.styling["text_field_padding"])
            + "px; }"
        )
        self.set_text_color(self.styling["colors"]["text_color"])
        self.set_background_color(self.styling["colors"]["text_background"])
        if styling_key:
            self.set_font(self.styling[styling_key])
        if num_lines:
            self.set_fixed_height_num_lines(num_lines)
        self.unfocus_on_click = unfocus_on_click

    def mousePressEvent(self, event):
        # Accept the mouse press event to allow text editing
        super().mousePressEvent(event)
        if self.unfocus_on_click:
            self.parent().setFocus()

    def keyPressEvent(self, event):
        if (
            event.key() in [Qt.Key_Return, Qt.Key_Enter]
            and not event.modifiers() == Qt.ShiftModifier
        ):
            self.stop_edit()
            self.parent().setFocus()
        # Remove whole line by pressing Cmd/Ctrl + Backspace
        elif (
            event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Backspace
        ):
            cursor = self.textCursor()
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            event.accept()
        # Call the default handler for other key events
        super().keyPressEvent(event)

    def set_fixed_height_num_lines(self, num_lines):
        font_metrics = QFontMetrics(self.font())
        line_height = font_metrics.lineSpacing()
        padding = self.styling["text_field_padding"]
        self.setFixedHeight(2 * padding + line_height * num_lines)

    def set_font(self, styling):
        font = QFont(styling["font"], styling["size"])
        font.setBold(styling["bold"])
        font.setItalic(styling["italic"])
        self.setFont(font)

    def set_text_color(self, color):
        self.setStyleSheet(self.styleSheet() + "QTextEdit { color: " + color + "; }")

    def set_background_color(self, color):
        self.setStyleSheet(
            self.styleSheet() + "QTextEdit { background-color: " + color + "; }"
        )

    def edit(self):
        self.setReadOnly(False)
        self.setFocus()
        self.moveCursor(QTextCursor.End)

    def stop_edit(self):
        self.setReadOnly(True)
        self.parent().setFocus()

    def insert_text(
        self, text, styling=None, new_line=False, first=False, indent=None, bold=False
    ):
        cursor = self.textCursor()
        if first:
            cursor.movePosition(QTextCursor.Start)
        else:
            cursor.movePosition(QTextCursor.End)

        if styling:
            format = QTextCharFormat()
            format.setFont(QFont(styling["font"], styling["size"]))
            format.setFontWeight(QFont.Bold if styling["bold"] else QFont.Normal)
            format.setFontItalic(styling["italic"])
            if "foreground" in styling:
                format.setForeground(QColor(styling["foreground"]))
            if "background" in styling:
                format.setBackground(QColor(styling["background"]))

        if indent:
            indentation = " " * indent
            lines = text.splitlines()
            indented_lines = []
            for line in lines:
                if len(line) > 0:
                    indented_lines.append(indentation + line)
            text = "\n".join(indented_lines)

        if new_line:
            cursor.insertBlock()

        if styling:
            cursor.insertText(text, format)
        else:
            format = cursor.charFormat()
            format.setFontWeight(QFont.Bold if bold else QFont.Normal)
            cursor.setCharFormat(format)
            cursor.insertText(text)

    def scroll_up(self):
        self.verticalScrollBar().triggerAction(
            self.verticalScrollBar().SliderSingleStepSub
        )

    def scroll_down(self):
        self.verticalScrollBar().triggerAction(
            self.verticalScrollBar().SliderSingleStepAdd
        )

    def scroll_to_index(self, pos):
        QTimer.singleShot(0, lambda: self._scroll_to_index(pos))

    def _scroll_to_index(self, position_idx):
        cursor = self.textCursor()
        cursor.setPosition(position_idx)
        self.setTextCursor(cursor)

        # Get the vertical and horizontal scrolling
        viewport = self.viewport()
        content_rect = (
            self.document().documentLayout().blockBoundingRect(cursor.block())
        )
        # Calculate the position to scroll to
        center_point = content_rect.topRight()
        scroll_area = viewport.rect()

        # Scroll so that the position is at 1/N of the window height from the top
        N = 4
        vertical_scroll = int(center_point.y() - scroll_area.height() // N)
        self.verticalScrollBar().setValue(vertical_scroll)

    def set_font_size(self, font_size):
        current_font = self.font()
        current_font.setPointSize(font_size)
        self.setFont(current_font)

    def scroll_to_top(self):
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(0))
