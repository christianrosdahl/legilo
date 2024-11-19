import os
import re
import unicodedata
from datetime import date, datetime

from PyQt5.QtCore import Qt

from autoread import autoread
from general_window import GeneralWindow
from main_window import MainWindow


class NewTextWindow(GeneralWindow):
    def __init__(self, data_dir, language, config, settings, dark_mode=False):
        super().__init__(dark_mode=dark_mode, title_height=110, text_field_width=800)

        self.horizontal_padding = 0

        self.data_dir = data_dir
        self.language = language
        self.config = config
        self.settings = settings

        instructions = (
            "Alt 1. Paste you text below and press [Enter] to proceed.\n"
            + "Alt 2. Paste an URL below and press [Enter] to fetch text.\n\n"
            + "(Use [Shift] + [Enter] to make a new line.)"
        )

        self.title_text.insert_text(instructions, styling=self.styling["main_text"])
        self.main_text.set_font_size(self.styling["new_text_size"])

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
                file_name = self.make_file_name(first_line)
                file_path = f"{self.data_dir}/{self.language}/texts/{file_name}"
                self.save_text_to_file(text, file_path)
                self.close()
                self.main_window = MainWindow(
                    self.data_dir,
                    self.language,
                    file_path,
                    self.config,
                    self.settings,
                )
                self.main_window.show()
                self.main_window.setFocus()

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
