from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDesktopWidget,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from styling import get_styling
from text_field import TextField


class GeneralWindow(QWidget):
    def __init__(
        self,
        config,
        dark_mode=False,
        title_height=70,
        show_app_name=False,
        text_field_width=500,
    ):
        super().__init__()

        self.config = config
        self.window_width = 800
        self.window_height = 1000
        self.vertical_padding = 50
        self.text_field_width = text_field_width
        self.title_height = title_height
        self.show_app_name = show_app_name
        self.styling = get_styling(self.config, dark_mode)
        self.setup_layout()

        self.setWindowTitle("Legilo")
        self.resize(self.window_width, self.window_height)
        self.setStyleSheet(
            "GeneralWindow { background-color:"
            + self.styling["colors"]["window_background_color"]
            + "; }"
        )
        self.center_on_screen()

        # Install event filter to capture key presses
        self.installEventFilter(self)

        self.editing = False

    def eventFilter(self, source, event):
        """Event filter to capture key presses"""
        if self.editing:
            enter_pressed = event.type() == event.KeyPress and event.key() in [
                Qt.Key_Return,
                Qt.Key_Enter,
            ]
            if not enter_pressed:
                return False

        if event.type() == event.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            # Close program with Cmd/Ctrl + W
            if key == Qt.Key_W and modifiers & Qt.ControlModifier:
                self.close()
                return True

            self.on_key_press(event)
        return super().eventFilter(source, event)

    def on_key_press(self, event):
        pass

    def setup_layout(self):
        layout = QHBoxLayout()
        vertical_layout = QVBoxLayout()

        # Add top padding
        vertical_layout.addSpacerItem(
            QSpacerItem(
                1, self.vertical_padding, QSizePolicy.Expanding, QSizePolicy.Fixed
            )
        )

        # Create and add the first text field
        if self.show_app_name:
            name_size = 65
            app_name_height = 100
            self.app_name_text = TextField(self.styling, styling_key="main_text")
            self.app_name_text.setMinimumWidth(self.text_field_width)
            self.app_name_text.setMinimumHeight(app_name_height)
            self.app_name_text.setMaximumHeight(app_name_height)
            self.app_name_text.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            self.app_name_text.set_background_color(
                self.styling["colors"]["window_background_color"]
            )
            self.app_name_text.setHtml(
                f'<div style="text-align: center; font-size:{name_size}px;">Legilo</div>'
            )
            vertical_layout.addWidget(self.app_name_text)

        # Create and add the second text field
        self.title_text = TextField(self.styling, styling_key="main_text")
        self.title_text.setMinimumWidth(self.text_field_width)
        self.title_text.setMinimumHeight(self.title_height)
        self.title_text.setMaximumHeight(self.title_height)
        self.title_text.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.title_text.set_background_color(
            self.styling["colors"]["window_background_color"]
        )
        vertical_layout.addWidget(self.title_text)

        # Create and add the third text field
        self.main_text = TextField(
            self.styling,
            styling_key="main_text",
            unfocus_on_click=False,
            hide_scrollbar=False,
        )
        self.main_text.setMinimumWidth(self.text_field_width)
        self.main_text.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        vertical_layout.addWidget(self.main_text)

        # Add bottom padding
        vertical_layout.addSpacerItem(
            QSpacerItem(
                1, self.vertical_padding, QSizePolicy.Expanding, QSizePolicy.Fixed
            )
        )

        left_spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        right_spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(left_spacer)
        layout.addLayout(vertical_layout)
        layout.addItem(right_spacer)

        # Set the layout to the main window
        self.setLayout(layout)

    def center_on_screen(self):
        """Center the window on the screen"""
        screen = QDesktopWidget().screenGeometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)
