import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog

from general_window import GeneralWindow
from main_window import MainWindow


class OpenFileWindow(GeneralWindow):
    def __init__(
        self, start_window, data_dir, language, config, settings, dark_mode=False
    ):
        super().__init__(
            config,
            start_window,
            dark_mode=dark_mode,
            show_app_name=True,
            title_height=40,
        )

        self.start_window = start_window
        self.data_dir = data_dir
        self.language = language
        self.config = config
        self.settings = settings
        self.selected = None
        self.file_path = None
        self.text_dir = f"{self.data_dir}/{language}/texts"
        self.titles_and_paths = self.get_titles_and_paths_for_texts(self.text_dir, 9)

        self.title_text.insert_text(
            "Select text to open:", styling=self.styling["main_text"]
        )
        self.show_options()

    def on_key_press(self, event):
        if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            if self.selected:
                event.accept()
                self.start_window.main_window = MainWindow(
                    self.start_window,
                    self.data_dir,
                    self.language,
                    self.file_path,
                    self.config,
                    self.settings,
                )
                self.start_window.main_window.show()
                self.start_window.main_window.setFocus()
                self.close()

        key_char = event.text().lower()
        options = ["o"]
        if self.titles_and_paths:
            options += [str(i) for i in range(1, len(self.titles_and_paths) + 1)]
        if key_char in options:
            self.selected = key_char
            if key_char == "o":
                self.file_path = self.select_file()
                self.title = self.file_path
                if not self.file_path:
                    self.selected = None
            else:
                (self.title, self.file_path) = self.titles_and_paths[int(key_char) - 1]
            self.show_options()

        return super().on_key_press(event)

    def show_options(self):
        self.main_text.clear()
        first_line = True
        if self.titles_and_paths:
            for i, (title, _) in enumerate(self.titles_and_paths, 1):
                line = f"[{i}] {title}"
                if first_line:
                    first_line = False
                else:
                    line = "\n" + line
                is_selected = self.selected == str(i)
                self.main_text.insert_text(line, bold=is_selected)
        self.main_text.insert_text("\n\n[O] Open other", bold=(self.selected == "o"))

        if self.selected:
            line = f'\n\nPress [Enter] to open "{self.title}"'
            self.main_text.insert_text(line)

    def get_first_lines_of_text_files(self, folder_path, num_files):
        first_lines = []

        # Get sorted list of files by last modified time
        files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]
        sorted_files = sorted(files, key=os.path.getmtime, reverse=True)

        for file_path in sorted_files:
            # Check if the file has a .txt extension
            if file_path.endswith(".txt"):
                try:
                    # Open the file and read the first line
                    with open(file_path, "r") as file:
                        first_line = file.readline().strip()
                        first_lines.append((first_line, file_path))
                    if len(first_lines) == num_files:
                        break
                except Exception as e:
                    print(f"Could not read {file_path}: {e}")

        return first_lines

    def get_titles_and_paths_for_texts(self, text_folder, num_texts, max_title_len=100):
        titles_and_paths = []
        first_lines = self.get_first_lines_of_text_files(text_folder, num_texts)
        for line, path in first_lines:
            if len(line) == 0:
                title = os.path.basename(path)
            elif len(line) > max_title_len:
                title = line[:max_title_len] + "..."
            else:
                title = line
            titles_and_paths.append((title, path))
        return titles_and_paths

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", self.text_dir, "Text Files (*.txt)"
        )
        return file_path
