import os
import re
import unicodedata
from datetime import date, datetime

from PyQt5.QtCore import Qt

from autoread import autoread
from general_window import GeneralWindow
from main_window import MainWindow


class NewTextWindow(GeneralWindow):
    def __init__(
        self,
        start_window,
        data_dir,
        language,
        config,
        settings,
        dark_mode=False,
        text_path=None,
        text=None,
    ):
        super().__init__(
            config,
            start_window,
            dark_mode=dark_mode,
            title_height=110,
            text_field_width=800,
        )

        self.horizontal_padding = 0

        self.start_window = start_window
        self.data_dir = data_dir
        self.language = language
        self.config = config
        self.settings = settings
        self.text_path = text_path
        self.text = text

        if self.text:
            instructions = (
                "Edit the text below and press [Enter] to continue.\n\n"
                + "(Use [Shift] + [Enter] to make a new line.)"
            )
        else:
            instructions = (
                "Alt. 1: Paste you text below and press [Enter] to proceed.\n"
                + "Alt. 2: Paste an URL below and press [Enter] to fetch text.\n\n"
                + "(Use [Shift] + [Enter] to make a new line.)"
            )

        self.title_text.insert_text(instructions, styling=self.styling["main_text"])
        self.main_text.set_font_size(self.styling["new_text_size"])

        if self.text:
            self.main_text.insert_text(self.text)
        self.main_text.edit()

    def on_key_press(self, event):
        if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            text = self.main_text.toPlainText()
            if len(text) == 0:
                self.main_text.edit()
                return
            first_line = text.split("\n")[0]
            if self.is_url(first_line):
                try:
                    (title, text) = autoread(first_line)
                except:
                    title = "Failed to fetch the page."
                    text = ""
                if len(title) > 0:
                    text = title + "\n\n" + text
                self.main_text.clear()
                self.main_text.insert_text(text)
                self.main_text.edit()
            else:
                if not self.text_path:
                    file_name = self.make_file_name(first_line)
                    self.text_path = (
                        f"{self.data_dir}/{self.language}/texts/{file_name}"
                    )
                self.save_text_to_file(text, self.text_path)
                self.start_window.main_window = MainWindow(
                    self.start_window,
                    self.data_dir,
                    self.language,
                    self.text_path,
                    self.config,
                    self.settings,
                )
                self.start_window.main_window.show()
                self.start_window.main_window.setFocus()
                self.close()

        return super().on_key_press(event)

    def is_url(self, string):
        url_pattern = re.compile(
            r"^(https?://)?"  # Optional scheme (http or https)
            r"(\w+\.)?"  # Optional subdomain
            r"[\w-]+\.\w+"  # Domain name and top-level domain
            r"([/?#]\S*)?$"  # Optional path, query, or fragment
        )
        return bool(url_pattern.match(string))

    def make_file_name(self, string):
        max_len = 70
        # Normalize the string to decompose characters with accents
        normalized_string = unicodedata.normalize("NFKD", string)
        # Remove accent characters by filtering out non-ASCII characters
        unaccented_string = "".join(
            c for c in normalized_string if not unicodedata.combining(c)
        )
        # Replace spaces with underscores and remove any non-alphanumeric characters (optional)
        file_name = re.sub(r"[^a-zA-Z0-9_ ]", "", unaccented_string).replace(" ", "_")

        if len(file_name) > 0:
            file_name = str(date.today()) + "_" + file_name
        else:
            file_name = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        if len(file_name) > max_len:
            file_name = file_name[:max_len]
        file_name += ".txt"
        return file_name

    def save_text_to_file(self, text, file_path):
        folder = os.path.dirname(file_path)
        if not os.path.exists(folder):
            os.makedirs(folder)

        with open(file_path, "w") as file:
            file.write(text)
