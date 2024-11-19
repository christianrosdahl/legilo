import json
import os
import pickle

from PyQt5.QtCore import Qt

from general_window import GeneralWindow
from new_text_window import NewTextWindow
from open_file_window import OpenFileWindow


class StartWindow(GeneralWindow):
    def __init__(self, data_dir, config_path):
        self.config = self.get_config(config_path)
        super().__init__(
            self.config, self, dark_mode=True, show_app_name=True, title_height=40
        )

        self.data_dir = data_dir
        self.settings_dir = data_dir + "/general"
        self.options = {"o": "open", "n": "new"}
        self.change_settings_keys = {"p": "pronounce", "d": "dark_mode"}
        self.settings = None
        forbidden_keys = list(self.options.keys()) + list(
            self.change_settings_keys.keys()
        )
        self.keys_to_languages = self.get_keys_to_languages(
            forbidden_keys=forbidden_keys
        )

        self.selected_language = None
        self.selected_action = None

        self.title_text.insert_text(
            "Press keyboard keys to select below:", styling=self.styling["main_text"]
        )
        self.load_settings()
        self.show_options()

    def on_key_press(self, event):
        if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            if self.selected_language and self.selected_action:
                self.hide()
                if self.selected_action == "new":
                    self.new_text_window = NewTextWindow(
                        self,
                        self.data_dir,
                        self.selected_language,
                        self.config,
                        self.settings,
                        self.settings["dark_mode"],
                    )
                    self.new_text_window.show()
                    self.new_text_window.setFocus()
                    self.new_text_window.main_text.edit()
                elif self.selected_action == "open":
                    self.open_file_window = OpenFileWindow(
                        self,
                        self.data_dir,
                        self.selected_language,
                        self.config,
                        self.settings,
                        dark_mode=True,
                    )
                    self.open_file_window.show()
                    self.open_file_window.setFocus()

        key_char = event.text().lower()
        if key_char in self.keys_to_languages:
            self.selected_language = self.keys_to_languages[key_char]
            self.show_options()
        elif key_char in self.options:
            self.selected_action = self.options[key_char]
            self.show_options()
        elif key_char in self.change_settings_keys:
            if self.change_settings_keys[key_char] == "pronounce":
                self.toggle_pronounce()
            elif self.change_settings_keys[key_char] == "dark_mode":
                self.toggle_dark_mode()
            self.show_options()

        return super().on_key_press(event)

    def get_config(self, config_file_path):
        try:
            with open(config_file_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Error: The config file '{config_file_path}' was not found.")
        except json.JSONDecodeError:
            print(f"Error: The config file '{config_file_path}' contains invalid JSON.")

    def get_keys_to_languages(self, forbidden_keys):
        keys_to_languages = {}
        next_number = 1
        if "languages" in self.config:
            for lang in self.config["languages"].keys():
                if len(lang) == 0:
                    continue
                first_letter = lang[0]
                if (
                    first_letter not in keys_to_languages.keys()
                    and first_letter not in forbidden_keys
                ):
                    keys_to_languages[first_letter] = lang
                else:
                    keys_to_languages[str(next_number)] = lang
                    next_number += 1
        return keys_to_languages

    def show_options(self):
        self.main_text.clear()
        self.main_text.insert_text("Select language:")
        for key, language in self.keys_to_languages.items():
            line = f"\n[{key.upper()}] {language.capitalize()}"
            is_selected = language == self.selected_language
            self.main_text.insert_text(line, bold=is_selected)

        self.main_text.insert_text("\n\nSelect option:")
        for key, action in self.options.items():
            line = f"\n[{key.upper()}] {action.capitalize()}"
            is_selected = action == self.selected_action
            self.main_text.insert_text(line, bold=is_selected)

        if self.selected_language and self.selected_action:
            line = "\n\nPress [Enter] to "
            if self.selected_action == "new":
                line += "create a new text in "
            elif self.selected_action == "open":
                line += "open a saved text in "
            line += self.selected_language.capitalize()
            self.main_text.insert_text(line)

        self.main_text.insert_text("\n\nSettings:")
        for key, setting in self.change_settings_keys.items():
            line = f"\n[{key.upper()}] "
            if setting == "pronounce":
                line += "Pronounce words: "
                if self.settings["sound_on"]:
                    line += "on"
                else:
                    line += "off"
            elif setting == "dark_mode":
                line += "Dark mode: "
                if self.settings["dark_mode"]:
                    line += "on"
                else:
                    line += "off"
            self.main_text.insert_text(line)

    def load_settings(self):
        try:
            with open(f"{self.settings_dir}/settings.pkl", "rb") as f:
                self.settings = pickle.load(f)
        except:
            self.settings = {"sound_on": True, "dark_mode": False}

    def save_settings(self):
        if not os.path.exists(self.settings_dir):
            os.makedirs(self.settings_dir)

        with open(f"{self.settings_dir}/settings.pkl", "wb") as f:
            pickle.dump(self.settings, f, pickle.HIGHEST_PROTOCOL)

    def toggle_pronounce(self):
        self.settings["sound_on"] = not self.settings["sound_on"]
        self.save_settings()
        self.show_options()

    def toggle_dark_mode(self):
        self.settings["dark_mode"] = not self.settings["dark_mode"]
        self.save_settings()
        self.show_options()
