import os
import platform
import re
import threading
import unicodedata
import webbrowser

from gtts import gTTS  # Generate mp3 files with Google's text-to-speech
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QDesktopWidget,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = ""
import pygame  # Play mp3 files from gtts
from googletrans import Translator

from autocomplete_line_text_field import AutocompleteLineTextField
from data_handler import DataHandler
from language_code import get_language_code
from sentence import get_first_sentence, get_sentences
from styling import get_styling
from text_field import TextField
from translate import LegiloTranslator
from word_with_article import word_with_article


class MainWindow(QWidget):
    def __init__(self, start_window, data_dir, language, text_path, config, settings):
        super().__init__()
        self.start_window = start_window
        self.data_dir = data_dir
        self.language = language
        self.text_path = text_path
        self.config = config
        self.settings = settings
        self.save_progress = True
        self.open_urls_in_same_tab = True
        self.styling = get_styling(self.config, settings["dark_mode"])
        text, active_word_num = self.get_text_from_file()
        self.text = text
        self.data = DataHandler(data_dir, language)
        self.legilo_translator = LegiloTranslator(
            language,
            use_lemma=self.config.get("use_lemmatizer"),
            lemmatizer_dir=f"{self.data_dir}/general/stanza",
        )

        self.active_word_num = active_word_num
        self.active_phrase = None
        self.active_info = None
        self.active_looked_up = False
        self.editing_personal_trans = False
        self.editing_lemmas = False
        self.editing_remark = False
        self.has_gone_through_whole_text = False
        self.phrase_selection_mode = False
        self.phrase_selection_mode_word = None
        self.selected_phrase_words = set()
        self.last_pronounced = None
        self.example_sentences = None
        self.remark_without_third_lang = None
        self.last_word_translated_to_thind_lang = None
        self.has_opened_new_browser_tab = False
        self.scrolling_in_text = False
        self.do_not_pronounce_next = False
        self.looking_up_new_phrase = False
        self.edit_text_after_closing_window = False

        # Setup window
        self.setWindowTitle("Legilo")
        self.resize(1300, 1000)
        self.center_on_screen()
        self.setStyleSheet(
            "MainWindow { background-color:"
            + self.styling["colors"]["window_background_color"]
            + "; }"
        )
        self.setup_layout()
        self.insert_main_text()

        # Get metadata for words, sentences and phrases in text
        self.text_words = self.get_text_words()
        self.num_text_words = len(self.text_words)
        self.text_sentences = self.get_text_sentences()
        self.text_phrases = self.get_text_phrases()

        self.mark_all_words()
        self.mark_all_phrases()

        # Set focus policy to accept keyboard input
        self.setFocusPolicy(Qt.StrongFocus)

        # Install event filter to capture key presses
        self.installEventFilter(self)

        # Connect cursor position change to highlight word by click
        self.main_text_field.cursorPositionChanged.connect(self.on_click)

        self.scroll_to_active_word()

        if self.settings["sound_on"]:
            pygame.mixer.init()  # Initialize mixer for playing sounds from Google TTS

    def eventFilter(self, source, event):
        """Event filter to capture key presses"""
        if self.editing_personal_trans or self.editing_remark or self.editing_lemmas:
            enter_pressed = event.type() == event.KeyPress and event.key() in [
                Qt.Key_Return,
                Qt.Key_Enter,
            ]
            if not enter_pressed:
                return False
        if event.type() == event.KeyPress:  # Check for key press event
            key = event.key()
            modifiers = event.modifiers()
            self.on_key_press(key, modifiers)
        return super().eventFilter(source, event)  # Pass the event to the parent class

    def closeEvent(self, event):
        self.handle_active()
        self.quit_and_clean_for_tts()
        if self.save_progress:
            self.data.save()
            self.save_text_with_active_word()
            print("The text was closed and your progress is saved.")
        else:
            print("The text was closed without saving your progress.")
        if not self.edit_text_after_closing_window:
            self.start_window.show()
        else:
            self.start_window.new_text(self.text_path, self.text)
        event.accept()

    def setup_layout(self):
        """Define layout for main window"""
        # Main horizontal layout
        main_layout = QHBoxLayout(self)

        # Left column layout
        left_column_layout = QVBoxLayout()

        # Left text field with 10 px padding
        self.main_text_field = TextField(
            self.styling, "left", "main_text", hide_scrollbar=False
        )
        self.main_text_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_text_field.setMaximumWidth(self.styling["main_text_max_width"])
        left_column_layout.addWidget(self.main_text_field)
        left_column_layout.setContentsMargins(10, 10, 10, 10)

        # Right column layout
        right_column_layout = QVBoxLayout()
        right_column_layout.setContentsMargins(10, 10, 10, 10)
        right_column_layout.setSpacing(
            0
        )  # Remove space between text fields in the right column

        # Category text field
        self.category_text_field = TextField(self.styling, "right", "category", 1)
        self.category_text_field.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )

        # Word text field
        self.word_text_field = TextField(self.styling, "right", "lookup_word", 1)
        self.word_text_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Edit personal translation text field
        self.personal_trans_text_field = TextField(
            self.styling, "right", "translation", 3
        )
        self.personal_trans_text_field.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        self.personal_trans_text_field.set_background_color(
            self.styling["colors"]["personal_translation_background"]
        )
        self.personal_trans_text_field.set_text_color(
            self.styling["colors"]["personal_translation_text"]
        )
        font = QFont(
            self.styling["translation"]["font"], self.styling["translation"]["size"]
        )
        self.personal_trans_text_field.setFont(font)
        self.personal_trans_text_field.hide()

        # Edit lemma text field
        self.lemma_text_field = AutocompleteLineTextField(
            self.styling, "right", "translation", 6
        )
        self.lemma_text_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.lemma_text_field.set_background_color(
            self.styling["colors"]["lemma_background"]
        )
        self.lemma_text_field.set_text_color(self.styling["colors"]["lemma_text"])
        font = QFont(
            self.styling["translation"]["font"], self.styling["translation"]["size"]
        )
        self.lemma_text_field.setFont(font)
        self.lemma_text_field.hide()

        # Translation text field (resizable)
        self.translation_text_field = TextField(
            self.styling, "right", "translation", hide_scrollbar=False
        )
        self.translation_text_field.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        # Remark text field
        self.remark_text_field = TextField(
            self.styling, "right", "remark", 10, hide_scrollbar=False
        )
        self.remark_text_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Example text field
        self.example_text_field = TextField(
            self.styling, "right", "example_translation", 5
        )
        self.example_text_field.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )

        # Titles in side field
        self.translations_title = SideFieldTitle("Translations:", self.styling)
        self.translations_title.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        self.notes_title = SideFieldTitle("Notes & Remarks:", self.styling)
        self.notes_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.example_title = SideFieldTitle("Example Sentence:", self.styling)
        self.example_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Add text fields to right column
        right_column_layout.addWidget(self.category_text_field)
        right_column_layout.addWidget(self.word_text_field)
        right_column_layout.addWidget(self.translations_title)
        right_column_layout.addWidget(self.personal_trans_text_field)
        right_column_layout.addWidget(self.lemma_text_field)
        right_column_layout.addWidget(self.translation_text_field)
        right_column_layout.addWidget(self.notes_title)
        right_column_layout.addWidget(self.remark_text_field)
        right_column_layout.addWidget(self.example_title)
        right_column_layout.addWidget(self.example_text_field)

        # Add columns to main_layout
        left_spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        right_spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        main_layout.addItem(left_spacer)
        main_layout.addLayout(left_column_layout, 3)
        main_layout.addLayout(right_column_layout, 2)
        main_layout.addItem(right_spacer)

        self.setLayout(main_layout)

    def center_on_screen(self):
        """Center the window on the screen"""
        screen = QDesktopWidget().screenGeometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

    def scroll_to_active_word(self):
        if self.active_word_num:
            self.scrolling_in_text = True
            text_idx = self.text_words[self.active_word_num]["start_idx"]
            self.main_text_field.scroll_to_index(text_idx)
        else:
            self.main_text_field.scroll_to_top()

    def get_text_from_file(self):
        metadata_tag = "# active_word_num = "
        with open(self.text_path, "r") as file:
            lines = file.readlines()
            text = "".join([line for line in lines if not metadata_tag in line]).strip()
            text = unicodedata.normalize("NFC", text)
            text = self.fix_paragraph_spacing(text)
            text = self.fix_title(text)
            metadata = [line for line in lines if metadata_tag in line]
            if len(metadata) == 0:
                active_word_num = False
            else:
                try:
                    active_word_num = int(metadata[0][len(metadata_tag) :])
                except Exception as e:
                    active_word_num = None

            return text, active_word_num

    def fix_paragraph_spacing(self, text):
        """Make sure that paragrahs are separated by two newlines"""
        return re.sub(r"(?<!\n)\n(?!\n)", "\n\n", text)

    def fix_title(self, text):
        """Add a title to the text if missing"""
        max_title_len = 100
        regex_sentence = r".*?[.!?](?:\s|$)|.*?(?:\n|$)"
        first_line = text.split("\n")[0]
        num_sentences_first_line = len(re.findall(regex_sentence, first_line))

        if num_sentences_first_line > 1 and len(first_line) >= max_title_len:
            sentences = re.finditer(regex_sentence, text)
            first_sentence = next(sentences).group().strip()
            # Remove period in title
            if len(first_sentence) > 0 and first_sentence[-1] == ".":
                first_sentence = first_sentence[:-1]
            text = first_sentence + "\n\n" + text

        return text

    def save_text_with_active_word(self):
        metadata_tag = "# active_word_num = "
        try:
            file_name = os.path.basename(self.text_path)
            self.text_path = f"{self.data_dir}/{self.language}/texts/{file_name}"
            with open(self.text_path, "w") as file:
                file.write(self.text)
                if self.active_word_num:
                    file.write("\n\n" + metadata_tag + str(self.active_word_num))
        except Exception as e:
            print(f"An error occurred: {e}")

    def on_key_press(self, key, modifiers):
        # Close window with Cmd/Ctrl + W
        if key == Qt.Key_W and modifiers & Qt.ControlModifier:
            self.close()
            return True

        # Close window, save, and edit opened text with Cmd/Ctrl + E
        if key == Qt.Key_E and modifiers & Qt.ControlModifier:
            self.edit_text_after_closing_window = True
            self.close()
            return True

        # Close window without saving for Cmd/Ctrl + X
        if key == Qt.Key_X and modifiers & Qt.ControlModifier:
            self.save_progress = False
            self.close()
            return True

        # Save data and active word with Cmd/Ctrl + S
        if key == Qt.Key_S and modifiers & Qt.ControlModifier:
            self.data.save()
            self.save_text_with_active_word()
            print("Data and active word were saved to file.")
            return True

        # Save data as text files with Cmd/Ctrl + R
        if key == Qt.Key_R and modifiers & Qt.ControlModifier:
            self.data.save_as_txt()
            print("Data was saved to text file.")
            return True

        number_keys = [ord(f"{i}") for i in range(0, 10)]

        if self.editing_personal_trans:
            if (
                key == Qt.Key_Return and not modifiers & Qt.ShiftModifier
            ) or key == Qt.Key_Up:
                self.update_personal_translation()
        elif self.editing_lemmas:
            if (
                key == Qt.Key_Return and not modifiers & Qt.ShiftModifier
            ) or key == Qt.Key_Up:
                self.update_lemmas()
        elif self.editing_remark:
            if (
                key == Qt.Key_Return and not modifiers & Qt.ShiftModifier
            ) or key == Qt.Key_Up:
                self.update_remark()
        else:
            if key in [Qt.Key_Right, Qt.Key_Space]:
                if modifiers & Qt.ShiftModifier:
                    self.go_to_next(skip_known=False)
                else:
                    self.go_to_next()
            elif key == Qt.Key_Left:
                if modifiers & Qt.ShiftModifier:
                    self.go_to_previous(skip_known=False)
                else:
                    self.go_to_previous()
            elif key in [Qt.Key_Up, Qt.Key_Return]:
                if modifiers & Qt.ControlModifier:
                    self.main_text_field.scroll_up()
                elif modifiers & Qt.ShiftModifier:
                    self.translation_text_field.scroll_up()
                elif modifiers & Qt.AltModifier:
                    self.remark_text_field.scroll_up()
                else:
                    if not self.active_looked_up:
                        if not self.phrase_selection_mode:
                            self.look_up()
                        else:  # If in phrase selection mode
                            self.select_word_num(self.phrase_selection_mode_word)
                    else:
                        self.go_to_next()
            elif key == Qt.Key_Down:
                if modifiers & Qt.ControlModifier:
                    self.main_text_field.scroll_down()
                elif modifiers & Qt.ShiftModifier:
                    self.translation_text_field.scroll_down()
                elif modifiers & Qt.AltModifier:
                    self.remark_text_field.scroll_down()
                else:
                    self.set_active_to_known()
            elif key in [Qt.Key_Delete, Qt.Key_Backspace]:
                self.set_active_to_ignored()
            elif key == ord("I"):
                self.edit_personal_translation()
            elif key == ord("U"):
                self.edit_lemmas()
            elif key == ord("R"):
                self.edit_remark()
            elif key == ord("O"):
                self.toggle_google_translation()
            elif key in number_keys:
                self.select_example_sentence(number_keys.index(key))
            elif key == ord("E"):
                self.toggle_phrase_selection_mode()
            elif key == ord("P"):
                self.pronounce_active()
            elif key == ord("H"):
                self.add_third_lang_trans()
            elif key == ord("A"):
                self.look_up_current_sentence()
            else:
                try:
                    key_char = chr(key)
                    if modifiers & Qt.ShiftModifier:
                        self.open_external_resource(key_char, lemma=True)
                    else:
                        self.open_external_resource(key_char)
                except ValueError:
                    pass

    def insert_main_text(self):
        lines = self.text.split("\n")
        first_line = True
        for line in lines:
            if first_line:
                self.main_text_field.insert_text(
                    line, self.styling["main_text_main_title"]
                )
            else:
                line = "\n" + line
                if self.line_is_title(line):
                    self.main_text_field.insert_text(
                        line, self.styling["main_text_title"]
                    )
                else:
                    self.main_text_field.insert_text(line, self.styling["main_text"])
            first_line = False

    def line_is_title(self, line):
        if len(line) > 50:
            return False
        if len(line) > 0 and line[-1] == ".":
            return False
        if len(line) > 0 and line[0] in ["-", "–", "—"]:
            return False
        return True

    def get_text_words(self):
        """Parse the text, store word data with start and end indices"""
        text_words = {}
        text = self.main_text_field.toPlainText().lower()
        words = text.split()

        # Regular expression to match words with letters and hyphens, excluding other punctuation
        # words = re.findall(r"\b\w+(?:[-']\w+)*\b", text)

        # Same as above, but also separates at apostrophes, so that "can't" -> ["can", "t"]
        words = re.findall(r"\b\w+(?:-\w+)*\b", text.replace("'", " "))

        start_idx = 0
        for word_num, word in enumerate(words, 1):
            start_idx = text.find(word, start_idx)
            end_idx = start_idx + len(word)
            text_words[word_num] = {
                "word": word,
                "start_idx": start_idx,
                "end_idx": end_idx,
            }
            start_idx = end_idx + 1  # Move to the next potential start index

        return text_words

    def get_text_phrases(self):
        """Get metadata about the phrases in the text (start and end indices, etc.)"""
        text_phrases = []
        phrases = self.data.phrases
        for word_num, word_metadata in self.text_words.items():
            word = word_metadata["word"]
            if word in phrases:
                phrases_for_word = phrases[word]
                for phrase in phrases_for_word:
                    phrase_words = phrase["phrase_words"]
                    if self.text_word_starts_phrase(word_num, phrase_words):
                        phrase_metadata = self.get_phrase_metadata(
                            word_num, phrase_words
                        )
                        text_phrases.append(phrase_metadata)
        return text_phrases

    def add_to_text_phrases(self, phrase_words):
        if not self.is_in_text_phrases(phrase_words):
            first_phrase_word = phrase_words[0]
            for word_num, word_metadata in self.text_words.items():
                word = word_metadata["word"]
                if word == first_phrase_word:
                    if self.text_word_starts_phrase(word_num, phrase_words):
                        phrase_metadata = self.get_phrase_metadata(
                            word_num, phrase_words
                        )
                        self.text_phrases.append(phrase_metadata)

    def remove_from_text_phrases(self, phrase_words):
        self.text_phrases = [
            phrase_metadata
            for phrase_metadata in self.text_phrases
            if phrase_metadata["words"] != phrase_words
        ]

    def is_in_text_phrases(self, phrase_words):
        for phrase_metadata in self.text_phrases:
            if phrase_metadata["words"] == phrase_words:
                return True
        return False

    def text_word_starts_phrase(self, word_num, phrase_words):
        if word_num + len(phrase_words) - 1 > self.num_text_words:
            return False
        for i, phrase_word in enumerate(phrase_words):
            if self.text_words[word_num + i]["word"] != phrase_word:
                return False
        return True

    def get_phrase_metadata(self, start_word_num, phrase_words):
        words = phrase_words
        end_word_num = start_word_num + len(phrase_words) - 1
        start_idx = self.text_words[start_word_num]["start_idx"]
        end_idx = self.text_words[end_word_num]["end_idx"]
        phrase_text = self.get_part_of_text(start_idx, end_idx)
        phrase_metadata = {
            "words": words,
            "phrase_text": phrase_text,
            "start_word_num": start_word_num,
            "end_word_num": end_word_num,
            "start_idx": start_idx,
            "end_idx": end_idx,
        }
        return phrase_metadata

    def get_part_of_text(self, start_idx, end_idx):
        cursor = self.main_text_field.textCursor()
        cursor.setPosition(start_idx)
        cursor.setPosition(end_idx, QTextCursor.KeepAnchor)
        return cursor.selectedText().strip()

    def get_text_phrase_for_word_num(self, word_num):
        for text_phrase in self.text_phrases:
            if text_phrase["start_word_num"] <= word_num <= text_phrase["end_word_num"]:
                return text_phrase
        return None

    def get_word(self, word_num):
        return self.text_words[word_num]["word"]

    def get_active_word(self):
        if self.active_word_num:
            return self.get_word(self.active_word_num)
        return None

    def get_active_word_or_phrase(self):
        if self.active_phrase:
            phrase_words = self.active_phrase["words"]
            return " ".join(phrase_words)
        return self.get_active_word()

    def highlight_word(self, word_num, foreground, background):
        """Highlight a word by its word number"""
        if word_num not in self.text_words:
            return

        # Get start and end index for the word
        word_metadata = self.text_words[word_num]
        start_idx = word_metadata["start_idx"]
        end_idx = word_metadata["end_idx"]

        # Highlight the word
        cursor = self.main_text_field.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setPosition(start_idx)
        cursor.setPosition(end_idx, QTextCursor.KeepAnchor)
        fmt = cursor.charFormat()
        fmt.setForeground(QColor(foreground))
        fmt.setBackground(QColor(background))
        cursor.setCharFormat(fmt)

    def mark_word(self, word_num, marker="category"):
        colors = self.styling["colors"]
        category_to_foreground = {
            "known": colors["text_color"],
            "ignored": colors["text_color"],
            "learning": colors["learning_text"],
            "new": colors["new_text"],
        }
        category_to_background = {
            "known": colors["text_background"],
            "ignored": colors["text_background"],
            "learning": colors["learning_background"],
            "new": colors["new_background"],
        }
        word = self.get_word(word_num)
        if marker == "category":
            category = self.get_category(word)
            self.highlight_word(
                word_num,
                category_to_foreground[category],
                category_to_background[category],
            )
        elif marker in category_to_foreground.keys():
            self.highlight_word(
                word_num, category_to_foreground[marker], category_to_background[marker]
            )
        elif marker == "active":
            self.highlight_word(
                word_num, colors["active_text"], colors["active_background"]
            )
        elif marker == "selected":
            self.highlight_word(
                word_num,
                colors["phrase_mode_marker_text"],
                colors["phrase_mode_marker"],
            )

    def mark_all_occurrences(self, word, marker="category"):
        for word_num, word_metadata in self.text_words.items():
            if word_metadata["word"] == word:
                self.mark_word(word_num, marker)

    def mark_all_words(self):
        for word_num in range(1, self.num_text_words + 1):
            self.mark_word(word_num)

    def mark_active_word(self, marker="active"):
        if self.active_word_num:
            self.mark_word(self.active_word_num, marker)

    def unmark_active_word(self):
        if self.active_word_num:
            self.mark_word(self.active_word_num)

    def mark_phrase(self, text_phrase, category):
        start_idx = text_phrase["start_idx"]
        end_idx = text_phrase["end_idx"]

        cursor = self.main_text_field.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setPosition(start_idx, QTextCursor.MoveAnchor)
        cursor.setPosition(end_idx, QTextCursor.KeepAnchor)
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(start, QTextCursor.MoveAnchor)
        while cursor.position() < end:
            cursor.movePosition(QTextCursor.NextWord - 1, QTextCursor.KeepAnchor)

            # Retrieve the current format of the word
            fmt = cursor.charFormat()
            if category == "ordinary":
                fmt.setFontUnderline(True)
                fmt.setFontItalic(False)
            elif category == "none":
                fmt.setFontUnderline(False)
                fmt.setFontItalic(False)
            elif category == "active":
                fmt.setFontUnderline(True)
                fmt.setFontItalic(True)
            cursor.setCharFormat(fmt)

            cursor.setPosition(cursor.position(), QTextCursor.MoveAnchor)

    def mark_active_phrase(self):
        if self.active_phrase:
            self.mark_phrase(self.active_phrase, "active")

    def mark_all_phrases(self):
        self.remove_phrase_markings()
        for text_phrase in self.text_phrases:
            self.mark_phrase(text_phrase, "ordinary")

    def remove_phrase_markings(self):
        cursor = self.main_text_field.textCursor()
        cursor.select(QTextCursor.Document)
        fmt = QTextCharFormat()
        fmt.setFontUnderline(False)
        fmt.setFontItalic(False)
        cursor.mergeCharFormat(fmt)

    def new_phrase(self, to_lower=True):
        word_num1 = min(self.selected_phrase_words)
        word_num2 = max(self.selected_phrase_words)
        start_idx = self.text_words[word_num1]["start_idx"]
        end_idx = self.text_words[word_num2]["end_idx"]
        phrase = self.get_part_of_text(start_idx, end_idx)
        if to_lower:
            phrase = phrase.lower()
        info = self.legilo_translator.get_info(phrase, is_phrase=True)
        info["word_type"] = "phrase"
        phrase_words = [
            self.get_word(word_num) for word_num in range(word_num1, word_num2 + 1)
        ]
        info["phrase_words"] = phrase_words
        (sentence, sentence_trans) = get_first_sentence(phrase, self.language)
        if len(sentence) > 0:
            info["sentence"] = sentence
            info["sentence_trans"] = sentence_trans
        self.active_info = info
        self.data.add_to_phrases(info)
        self.add_to_text_phrases(phrase_words)
        self.active_phrase = self.get_text_phrase_for_word_num(word_num1)
        self.unmark_active_word()
        self.mark_active_phrase()
        self.looking_up_new_phrase = True
        self.look_up()
        self.looking_up_new_phrase = False
        self.active_looked_up = True

    def look_up(self):
        if self.active_phrase:
            self.look_up_phrase()
        elif self.active_word_num:
            self.look_up_word()

    def look_up_word(self):
        word = self.get_active_word()
        category = self.get_category(word)
        known_without_info = category == "known" and not self.data.known_words[word]
        if category in ["new", "ignored"] or known_without_info:
            info = self.legilo_translator.get_info(word)
            (sentence, sentence_trans) = get_first_sentence(word, self.language)
            if len(sentence) > 0:
                info["sentence"] = sentence
                info["sentence_trans"] = sentence_trans
        elif category == "learning":
            info = self.data.learning_words[word]
        else:  # category == 'known' and word has info
            info = self.data.known_words[word]

        self.active_info = info
        self.active_looked_up = True
        self.show_lookup_word()

    def look_up_phrase(self):
        self.clear_side_field()
        if self.active_phrase:
            self.unmark_active_word()
            phrase_words = self.active_phrase["words"]
            info = self.data.get_phrase(phrase_words)
            self.active_info = info
            self.active_looked_up = True
            self.show_lookup_word()

    def show_lookup_word(self):
        self.show_active_word()
        self.show_category()
        self.show_translation()
        self.show_remark()
        self.show_example()
        if self.settings["sound_on"]:
            self.pronounce_active()

    def show_active_word(self):
        self.word_text_field.clear()
        style = self.styling["lookup_word"]
        style["foreground"] = self.styling["colors"]["text_color"]
        if self.active_phrase:
            word = self.active_phrase["phrase_text"]
        else:
            info = self.active_info
            word = info.get("dict_word")
            if "word_type" in info and "noun" in info["word_type"].split(", "):
                # Add the lines below to show the word both without and with article
                # and gender color if it's not just a noun, but also e.g. a verb
                # if not info["word_type"] == "noun":  # Not just noun
                #     self.word_text_field.insert_text(word + ", ", style)

                has_unique_gender = "gender" in info and len(info["gender"]) == 1
                word_is_variant = "lemmas" in info and not word in [
                    lemma.lower() for lemma in info["lemmas"]
                ]

                if self.language == "german":
                    word = word.capitalize()
                if has_unique_gender:
                    gender = info["gender"]
                    color = self.styling["colors"]["gender_colors"][gender]
                    style["foreground"] = color
                    if not word_is_variant:
                        word = word_with_article(word, gender, self.language)

        self.word_text_field.insert_text(word, style)

    def show_category(self):
        self.category_text_field.clear()
        if self.active_phrase:
            phrase_words = self.active_phrase["words"]
            if self.looking_up_new_phrase:
                category = "new phrase"
                foreground = self.styling["colors"]["new_text"]
                background = self.styling["colors"]["new_background"]
            else:
                category = "saved phrase"
                foreground = self.styling["colors"]["learning_text"]
                background = self.styling["colors"]["learning_background"]
        else:
            word = self.get_active_word()
            category = self.get_category(word)
            if category == "ignored":
                category = "new"
            if category == "learning":
                foreground = self.styling["colors"]["learning_text"]
                background = self.styling["colors"]["learning_background"]
            elif category == "new":
                foreground = self.styling["colors"]["new_text"]
                background = self.styling["colors"]["new_background"]
            elif category == "known":
                foreground = self.styling["colors"]["known_text"]
                background = self.styling["colors"]["known_background"]

        style = self.styling["category"]
        style = {**style, "foreground": foreground}
        self.category_text_field.set_background_color(background)
        self.category_text_field.insert_text(category, style)

    def show_translation(
        self, show_personal_trans=True, show_google_trans=True, show_lemmas=True
    ):
        self.translation_text_field.clear()
        trans = self.active_info["trans"]
        lemmas = set()
        if "lemmas" in self.active_info:
            lemmas = self.active_info["lemmas"]
        style = self.styling["translation"]
        style_italic = {**style, "italic": True}
        style_word = {**style, "bold": True}
        style_parenthesis = {**style}
        style_type_and_gender = {**style, "italic": True}
        style_personal_translation = {
            **style,
            "foreground": self.styling["colors"]["personal_translation_text"],
            "background": self.styling["colors"]["personal_translation_background"],
        }
        style_google_translate = {
            **style,
            "foreground": self.styling["colors"]["google_translate_text"],
            "background": self.styling["colors"]["google_translate_background"],
        }
        style_definitions = {**style}
        style_synonyms = {
            **style,
            "size": self.styling["translation"]["size"] - 2,
            "bold": True,
        }

        # Show lemmas and possible personal translations for them
        if show_lemmas:
            if len(lemmas) > 0:
                self.translation_text_field.insert_text("Form of ", style_italic)
            lemmas_with_translation = {}
            lemmas_without_translation = []
            for lemma in lemmas:
                personal_lemma_trans = self.get_personal_translation(lemma)
                if personal_lemma_trans:
                    lemmas_with_translation[lemma] = personal_lemma_trans
                else:
                    lemmas_without_translation.append(lemma)

            count = 0
            for lemma, lemma_trans in lemmas_with_translation.items():
                self.translation_text_field.insert_text(f"{lemma}", style_word)
                self.translation_text_field.insert_text(": ", style)
                self.translation_text_field.insert_text(lemma_trans, style)
                if count < len(lemmas) - 1:
                    self.translation_text_field.insert_text(", ", style)
                count += 1
            for lemma in lemmas_without_translation:
                self.translation_text_field.insert_text(f"{lemma}", style_word)
                if count < len(lemmas) - 1:
                    self.translation_text_field.insert_text(", ", style)
                count += 1

            if len(lemmas) > 0:
                self.translation_text_field.insert_text("\n\n", style)

        # Show Wiktionary translations
        google_trans = None
        for i, item in enumerate(trans):
            if "source" in item and item["source"] == "Google Translate":
                if "definitions" in item:
                    definition = item["definitions"][0]
                    if "definition" in definition:
                        google_trans = definition["definition"]

            elif "source" in item and item["source"] == "Wiktionary":
                if "word" in item:
                    self.translation_text_field.insert_text(item["word"], style_word)
                if "part_of_speech" in item:
                    self.translation_text_field.insert_text(" (", style_parenthesis)
                    self.translation_text_field.insert_text(
                        item["part_of_speech"], style_type_and_gender
                    )
                    if "gender" in item:
                        self.translation_text_field.insert_text(
                            " — " + item["gender"], style_type_and_gender
                        )
                    self.translation_text_field.insert_text(")", style_parenthesis)
                    if "qualifier" in item:
                        self.translation_text_field.insert_text(" (", style_parenthesis)
                        self.translation_text_field.insert_text(
                            item["qualifier"], style_type_and_gender
                        )
                        self.translation_text_field.insert_text(")", style_parenthesis)

                if "definitions" in item:
                    for j, definition in enumerate(item["definitions"]):
                        if "definition" in definition:
                            def_def = definition["definition"]
                            self.translation_text_field.insert_text(
                                f"{j+1}. {def_def}",
                                style_definitions,
                                new_line=True,
                                indent=4,
                            )
                        if "synonyms" in definition:
                            synonyms = definition["synonyms"]
                            self.translation_text_field.insert_text(
                                f"≈ {synonyms}",
                                style_synonyms,
                                new_line=True,
                                indent=10,
                            )
                        if "antonyms" in definition:
                            antonyms = definition["antonyms"]
                            self.translation_text_field.insert_text(
                                f"≠ {antonyms}",
                                style_synonyms,
                                new_line=True,
                                indent=10,
                            )
                has_more_wiktionary_translations = (
                    i < len(trans) - 1
                    and "source" in trans[i + 1]
                    and trans[i + 1]["source"] == "Wiktionary"
                )
                if has_more_wiktionary_translations:
                    self.translation_text_field.insert_text("\n\n", style)

        # Show Google translation if available
        if show_google_trans and google_trans:
            self.translation_text_field.insert_text("\n\n", style, first=True)
            self.translation_text_field.insert_text(
                google_trans, style_google_translate, first=True
            )

        # Show personal translation if available
        personal_trans = self.get_personal_translation()
        if show_personal_trans and personal_trans:
            self.translation_text_field.insert_text("\n\n", style, first=True)
            self.translation_text_field.insert_text(
                personal_trans, style_personal_translation, first=True
            )

    def show_remark(self):
        self.remark_text_field.clear()
        info = self.active_info
        if "remark" in info:
            self.remark_text_field.insert_text(info["remark"])

    def show_example(self):
        self.example_text_field.clear()
        info = self.active_info
        if "sentence" in info and "sentence_trans" in info:
            self.example_text_field.insert_text(
                info["sentence"], styling=self.styling["example"]
            )
            self.example_text_field.insert_text(
                info["sentence_trans"],
                styling=self.styling["example_translation"],
                new_line=True,
            )

    def clear_side_field(self):
        self.category_text_field.clear()
        self.category_text_field.set_background_color(
            self.styling["colors"]["text_background"]
        )
        self.word_text_field.clear()
        self.translation_text_field.clear()
        self.remark_text_field.clear()
        self.example_text_field.clear()
        self.active_looked_up = False

    def set_new_to_known(self, start_word_num, end_word_num):
        if start_word_num <= end_word_num:
            for word_num in range(start_word_num, end_word_num + 1):
                word = self.get_word(word_num)
                if self.is_new(word):
                    self.data.add_to_known(word)
                    self.mark_all_occurrences(word, "known")

    def set_active_word_num(self, active_word_num):
        if self.active_word_num:
            self.unmark_active_word()
            previous_word_num = self.active_word_num
        else:
            previous_word_num = 1
        self.active_word_num = active_word_num
        if self.active_word_num:
            self.set_new_to_known(previous_word_num, self.active_word_num - 1)
            self.mark_active_word()
        elif self.has_gone_through_whole_text:
            self.set_new_to_known(previous_word_num, self.num_text_words)
        elif not self.active_word_num == 1:
            self.set_new_to_known(1, self.active_word_num - 1)
        self.active_info = None

    def set_phrase_selection_mode_word(self, word_num):
        current_word_num = self.phrase_selection_mode_word
        if current_word_num and not current_word_num in self.selected_phrase_words:
            self.mark_word(current_word_num)
        self.phrase_selection_mode_word = word_num
        if word_num:
            self.mark_word(word_num, "selected")

    def on_click(self):
        """Look up clicked word and mark previous new words as known"""
        cursor = self.main_text_field.textCursor()
        pos = cursor.position()
        if not self.scrolling_in_text:
            self.select_text_position(pos)
        else:
            self.select_text_position(pos, look_up=False)
            self.scrolling_in_text = False

    def select_text_position(self, text_idx, look_up=True):
        selected_word_num = self.index_to_word_num(text_idx)
        if self.phrase_selection_mode:
            selected_phrase = self.index_to_phrase(text_idx)
            if selected_phrase:
                self.active_phrase = selected_phrase
                self.unmark_active_word()
                self.mark_active_phrase()
                self.look_up()
                self.deactivate_phrase_selection_mode()
            elif selected_word_num:
                if self.active_word_num:
                    self.mark_word(self.active_word_num)
                self.mark_word(selected_word_num, "selected")
                self.selected_phrase_words.add(selected_word_num)
                if len(self.selected_phrase_words) == 2:
                    self.new_phrase()
                    self.deactivate_phrase_selection_mode()
        elif selected_word_num:
            self.handle_active()
            self.set_active_word_num(selected_word_num)
            if look_up:
                self.look_up()

    def select_word_num(self, word_num):
        text_idx = self.text_words[word_num]["start_idx"]
        self.select_text_position(text_idx)

    def index_to_word_num(self, text_idx):
        """Find the word number by position"""
        for word_num, word_metadata in self.text_words.items():
            if word_metadata["start_idx"] <= text_idx <= word_metadata["end_idx"]:
                return word_num
        return None

    def index_to_phrase(self, text_idx):
        for text_phrase in self.text_phrases:
            if text_phrase["start_idx"] <= text_idx <= text_phrase["end_idx"]:
                return text_phrase
        return None

    def word_num_to_phrase(self, word_num):
        for text_phrase in self.text_phrases:
            if text_phrase["start_word_num"] <= word_num <= text_phrase["end_word_num"]:
                return text_phrase
        return None

    def go_to_next(self, skip_known=True, save=True):
        if self.phrase_selection_mode:
            self.phrase_selection_next()
            return
        if self.active_phrase:
            self.handle_active(save)
            self.mark_active_word()
            return
        self.handle_active(save)
        if skip_known:
            next_word_num = self.next_marked_word_num(self.active_word_num)
        else:
            next_word_num = self.next_word_num(self.active_word_num)
        if not next_word_num:
            self.has_gone_through_whole_text = True
        self.set_active_word_num(next_word_num)

    def go_to_previous(self, skip_known=True, save=True):
        if self.phrase_selection_mode:
            self.phrase_selection_previous()
            return
        if self.active_phrase:
            return
        self.handle_active(save)
        if skip_known:
            previous_word_num = self.previous_marked_word_num(self.active_word_num)
        else:
            previous_word_num = self.previous_word_num(self.active_word_num)
        self.set_active_word_num(previous_word_num)

    def phrase_selection_next(self):
        current_word_num = self.phrase_selection_mode_word
        next_word_num = self.next_word_num(current_word_num)
        self.set_phrase_selection_mode_word(next_word_num)

    def phrase_selection_previous(self):
        current_word_num = self.phrase_selection_mode_word
        previous_word_num = self.previous_word_num(current_word_num)
        self.set_phrase_selection_mode_word(previous_word_num)

    def set_active_to_known(self):
        if self.active_phrase:
            self.delete_active_phrase()
            self.active_phrase = None
            self.mark_active_word()
        else:
            self.save_active_word_as("known")
            self.go_to_next(save=False)

    def set_active_to_ignored(self):
        if not self.active_phrase:
            self.save_active_word_as("ignored")
            self.go_to_next(save=False)

    def handle_active(self, save=True):
        if self.active_phrase:
            if save:
                self.save_active_phrase()
            else:
                self.delete_active_phrase()
            self.active_phrase = False
            self.mark_active_word()
        elif self.active_word_num:
            category = self.get_active_word_category()
            if self.active_looked_up:
                if save:
                    self.save_active_word_as("learning")
                elif category == "new":
                    self.save_active_word_as("known")

    def edit_personal_translation(self):
        if not self.active_looked_up:
            return
        self.editing_personal_trans = True
        personal_translation = self.get_personal_translation()
        if personal_translation:
            self.personal_trans_text_field.insert_text(personal_translation)
        self.show_translation(show_personal_trans=False)
        self.personal_trans_text_field.show()
        self.personal_trans_text_field.edit()

    def update_personal_translation(self):
        new_trans = self.personal_trans_text_field.toPlainText()
        self.personal_trans_text_field.stop_edit()
        self.personal_trans_text_field.clear()
        self.personal_trans_text_field.hide()
        self.editing_personal_trans = False

        word_or_phrase = self.get_active_word_or_phrase()
        self.data.remove_personal_translation(word_or_phrase)
        if len(new_trans) > 0:
            self.data.add_personal_translation(word_or_phrase, new_trans)
        self.show_translation()

    def edit_lemmas(self):
        if not self.active_looked_up:
            return
        self.editing_lemmas = True
        lemmas = None
        first_line = True
        if "lemmas" in self.active_info:
            lemmas = self.active_info["lemmas"]
            for lemma in lemmas:
                if not first_line:
                    self.lemma_text_field.insert_text("\n")
                if lemma in self.data.personal_translations:
                    trans = self.data.personal_translations[lemma]
                    self.lemma_text_field.insert_text(f"{lemma}: {trans}")
                else:
                    self.lemma_text_field.insert_text(f"{lemma}")
                first_line = False
        self.show_translation(show_lemmas=False)
        suggestions = self.data.get_all_words(True, [self.get_active_word_or_phrase()])
        self.lemma_text_field.set_suggestions(suggestions)
        self.lemma_text_field.show()
        self.lemma_text_field.edit()

    def update_lemmas(self):
        lemma_data = self.lemma_text_field.toPlainText()
        previous_lemmas = None
        if "lemmas" in self.active_info:
            previous_lemmas = self.active_info["lemmas"]
        lemmas = set()
        for line in lemma_data.split("\n"):
            line_parts = line.split(":")
            lemma = line_parts[0].strip()
            lemma = unicodedata.normalize("NFC", lemma)
            if len(lemma) == 0:
                continue
            if len(line_parts) > 1:
                trans = line_parts[1].strip()
                if len(trans) > 0:
                    self.data.add_personal_translation(lemma, trans)
                else:
                    self.data.remove_personal_translation(lemma)
            else:
                self.data.remove_personal_translation(lemma)
            lemmas.add(lemma)
        self.active_info["lemmas"] = lemmas
        if lemmas != previous_lemmas:
            word = self.active_info["dict_word"]
            is_phrase = False
            if self.active_phrase:
                is_phrase = True
            old_info = self.active_info
            new_info = self.legilo_translator.get_info(
                word,
                is_phrase=is_phrase,
                include_google_trans=self.has_google_translation(),
                word_lemmas=lemmas,
            )
            for key, value in old_info.items():
                if not key in new_info:
                    new_info[key] = value
            self.active_info = new_info
        self.lemma_text_field.stop_edit()
        self.lemma_text_field.clear()
        self.lemma_text_field.hide()
        self.editing_lemmas = False
        self.show_translation()

    def get_personal_translation(self, word=None):
        if not word:
            word = self.get_active_word_or_phrase()
        if word in self.data.personal_translations:
            return self.data.personal_translations[word]
        return None

    def toggle_google_translation(self):
        if not self.active_looked_up:
            return

        if self.has_google_translation():
            self.delete_google_translation()
        else:
            trans_list = self.active_info["trans"]
            word = self.get_active_word()
            google_trans = self.legilo_translator.get_google_translation(word)
            trans_list += google_trans
        self.show_translation()

    def has_google_translation(self):
        """Check if word translations list contains a Google translation"""
        trans = self.active_info["trans"]
        for item in trans:
            if "source" in item and item["source"] == "Google Translate":
                return True
        return False

    def delete_google_translation(self):
        """Delete Google translation from translations list, if available"""
        trans = self.active_info["trans"]
        translation_index_to_remove = None
        for i, item in enumerate(trans):
            if "source" in item and item["source"] == "Google Translate":
                translation_index_to_remove = i
                break
        if translation_index_to_remove is not None:
            del trans[translation_index_to_remove]

    def edit_remark(self):
        if not self.active_looked_up:
            return
        self.editing_remark = True
        self.remark_text_field.edit()

    def update_remark(self):
        self.remark_text_field.stop_edit()
        self.editing_remark = False

        remark = self.remark_text_field.toPlainText()
        self.active_info["remark"] = remark

    def next_word_num(self, active_word_num):
        if active_word_num:
            next_word_num = active_word_num + 1
        else:
            next_word_num = 1
        if next_word_num > self.num_text_words:
            return None
        return next_word_num

    def previous_word_num(self, active_word_num):
        if not active_word_num:
            return None
        previous_word_num = active_word_num - 1
        if previous_word_num < 1:
            return None
        return previous_word_num

    def next_marked_word_num(self, active_word_num):
        if active_word_num:
            next_word_num = active_word_num + 1
        else:
            next_word_num = 1

        while True:
            if next_word_num > self.num_text_words:
                return None
            if self.is_marked(self.get_word(next_word_num)):
                return next_word_num
            next_word_num += 1

    def previous_marked_word_num(self, active_word_num):
        if not active_word_num:
            return None
        previous_word_num = active_word_num - 1
        while True:
            if previous_word_num < 1:
                return None
            if self.is_marked(self.get_word(previous_word_num)):
                return previous_word_num
            previous_word_num -= 1

    def is_learning(self, word):
        return word in self.data.learning_words.keys()

    def is_known(self, word):
        return word in self.data.known_words.keys()

    def is_ignored(self, word):
        return word in self.data.ignored_words

    def get_category(self, word):
        if self.is_learning(word):
            return "learning"
        elif self.is_ignored(word):
            return "ignored"
        elif self.is_known(word):
            return "known"
        else:
            return "new"

    def get_active_word_category(self):
        word = self.get_active_word()
        return self.get_category(word)

    def save_active_word_as(self, category):
        if self.active_word_num:
            word = self.get_active_word()
            info = self.active_info
            if category == "learning":
                self.data.add_to_learning(word, info)
            elif category == "ignored":
                self.data.add_to_ignored(word)
            elif category == "known":
                self.data.add_to_known(word, info)
            elif category == "new":
                self.data.remove_word(word, info)
            self.mark_all_occurrences(word, category)
        self.clear_side_field()

    def save_active_phrase(self):
        if self.active_phrase:
            phrase_words = self.active_phrase["words"]
            info = self.active_info
            self.data.add_to_phrases(info)
            self.add_to_text_phrases(phrase_words)
            self.mark_all_phrases()
        self.clear_side_field()

    def delete_active_phrase(self):
        if self.active_phrase:
            info = self.active_info
            phrase_words = self.active_phrase["words"]
            self.data.remove_from_phrases(info)
            self.remove_from_text_phrases(phrase_words)
            self.mark_all_phrases()
        self.clear_side_field()

    def is_new(self, word):
        return self.get_category(word) == "new"

    def is_marked(self, word):
        return self.get_category(word) in ["new", "learning"]

    def pronounce(self, word, language):
        threading.Thread(target=self.text_to_speech, args=(word, language)).start()

    def text_to_speech(self, word, language):
        """Pronounce using Google's text-to-speech"""
        if not (self.last_pronounced and self.last_pronounced == word):
            tts = gTTS(text=word, lang=get_language_code(language))
            tts.save(self.data_dir + "/general/last_text_to_speech.mp3")
            self.last_pronounced = word
        pygame.mixer.music.load(self.data_dir + "/general/last_text_to_speech.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    def quit_and_clean_for_tts(self):
        if self.settings["sound_on"]:
            pygame.mixer.quit()
            file_path = self.data_dir + "/general/last_text_to_speech.mp3"
            if os.path.exists(file_path):
                os.remove(file_path)

    def pronounce_active(self):
        if self.do_not_pronounce_next:
            self.do_not_pronounce_next = False
            return
        if self.active_looked_up:
            # Get word with possible article
            word = self.word_text_field.toPlainText()
            self.pronounce(word, self.language)
        elif self.active_word_num:
            self.pronounce(self.get_active_word(), self.language)

    def select_example_sentence(self, example_num):
        if not self.active_looked_up:
            return
        if self.active_phrase:
            word = self.active_phrase["phrase_text"]
        else:
            word = self.get_active_word()
        examples = self.example_sentences
        if not examples or word != examples["word"]:
            (sentences, sentences_trans) = get_sentences(word, self.language, 8)
            examples = {
                "word": word,
                "sentences": sentences,
                "sentences_trans": sentences_trans,
            }
            self.examples = examples
        if 1 <= example_num <= 8:
            sentence = examples["sentences"][example_num - 1]
            sentence_trans = examples["sentences_trans"][example_num - 1]
        elif example_num == 9 and not self.active_phrase:
            sentence = self.get_active_sentence()
            translator = Translator()
            sentence_trans = translator.translate(
                sentence, src=get_language_code(self.language), dest="en"
            ).text
        else:  # Don't use any example sentence if example_num == 0
            sentence = ""
            sentence_trans = ""

        info = self.active_info
        info["sentence"] = sentence
        info["sentence_trans"] = sentence_trans
        self.show_example()

    def get_text_sentences(self):
        """Get metadata about the sentences in the text (start and end indices, etc.)"""
        text = self.main_text_field.toPlainText()
        # Match sentences, making sure punctuation is included as part of the sentence
        sentences = re.finditer(r".*?[.!?](?:\s|$)|.*?(?:\n|$)", text)

        result = {}

        for match in sentences:
            sentence = match.group()
            if not sentence.strip():  # Skip empty matches from excessive newlines
                continue

            start_idx = match.start()
            end_idx = match.end()
            start_word_num = None
            end_word_num = None
            words = []
            word_nums = []

            for word_num, word_metadata in self.text_words.items():
                if start_idx <= word_metadata["start_idx"] < end_idx:
                    if not start_word_num:
                        start_word_num = word_num
                    end_word_num = word_num
                    words.append(self.get_word(word_num))
                    word_nums.append(word_num)

            for word_num in word_nums:
                result[word_num] = {
                    "words": words,
                    "text": self.get_part_of_text(start_idx, end_idx),
                    "start_word_num": start_word_num,
                    "end_word_num": end_word_num,
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                }

        return result

    def get_active_sentence(self):
        text_sentence = self.text_sentences[self.active_word_num]
        start_idx = text_sentence["start_idx"]
        end_idx = text_sentence["end_idx"]
        return self.get_part_of_text(start_idx, end_idx)

    def toggle_phrase_selection_mode(self):
        if self.phrase_selection_mode:
            self.deactivate_phrase_selection_mode()
            self.hide_phrase_mode_info()
        else:
            self.activate_phrase_selection_mode()

    def activate_phrase_selection_mode(self):
        self.handle_active()
        self.phrase_selection_mode = True
        self.show_phrase_mode_info()
        self.set_phrase_selection_mode_word(self.active_word_num)

    def deactivate_phrase_selection_mode(self):
        self.phrase_selection_mode = False
        self.set_phrase_selection_mode_word(None)
        for word_num in self.selected_phrase_words:
            self.mark_word(word_num)
        self.selected_phrase_words = set()
        if self.active_word_num and not self.active_looked_up:
            self.mark_active_word()

    def show_phrase_mode_info(self):
        style = self.styling["translation"]
        style_title = {**style, "bold": True}
        phrase_mode_info1 = "Phrase Mode activated!\n\n"
        self.translation_text_field.insert_text(phrase_mode_info1, styling=style_title)
        phrase_mode_info2 = (
            "Select a saved phrase (underlined) or look up a new phrase "
            + "by selecting its first and last words."
        )
        self.translation_text_field.insert_text(phrase_mode_info2, styling=style)

    def hide_phrase_mode_info(self):
        self.translation_text_field.clear()

    def add_third_lang_trans(self):
        if self.active_looked_up:
            word = self.active_info["dict_word"]
            trans = self.active_info["trans"]
            # Remove translation if already added
            if word == self.last_word_translated_to_thind_lang:
                self.active_info["remark"] = self.remark_without_third_lang
                self.last_word_translated_to_thind_lang = None
            # Otherwise, add third language translation
            else:
                if not "remark" in self.active_info:
                    self.active_info["remark"] = ""
                self.remark_without_third_lang = self.active_info["remark"]
                self.last_word_translated_to_thind_lang = word
                third_lang = self.config["third_language"]
                third_lang_trans = f"{third_lang.capitalize()} translations:\n"
                third_lang_trans += self.translate_to_third_lang(word, trans)
                new_remark = self.active_info["remark"]
                if len(self.active_info["remark"]) > 0:
                    new_remark += "\n\n"
                new_remark += third_lang_trans
                self.active_info["remark"] = new_remark
            self.show_remark()

    def translate_to_third_lang(self, word, trans):
        translator = Translator()
        translations = []

        # Translate the original word directly to third_lang
        third_lang_trans = translator.translate(
            word,
            src=get_language_code(self.language),
            dest=get_language_code(self.config["third_language"]),
        ).text
        translations.append(word + " = " + third_lang_trans)

        # Translate the English translations to third_lang
        definitions = self.definitions_to_list(trans)
        for definition in definitions:
            third_lang_trans = translator.translate(
                definition,
                src="en",
                dest=get_language_code(self.config["third_language"]),
            ).text
            translations.append(definition + " = " + third_lang_trans)

        if len(translations) == 0:
            return ""

        return ", ".join(translations)

    def definitions_to_list(self, translations):
        """
        Get definitions as a list with only definition strings.
        Skips definitions that have several lines.
        """
        def_strings = []
        for translation in translations:
            if "definitions" in translation:
                for definition_entry in translation["definitions"]:
                    if "definition" in definition_entry:
                        definition = definition_entry["definition"]
                        # Don't use multiple-line definitions and skip definitions
                        # of type "masculine plural of ..."
                        if not definition.count("\n") > 1 and not " of " in definition:
                            # Remove words in parentheses
                            definition = re.sub(r"\([^)]*\)", "", definition)
                            definition = definition.replace(";", ",")
                            definition_parts = definition.split(", ")
                            for part in definition_parts:
                                def_strings.append(part.strip())

        return def_strings

    def look_up_current_sentence(self):
        if self.active_word_num and not self.phrase_selection_mode:
            self.activate_phrase_selection_mode()
            text_sentence = self.text_sentences[self.active_word_num]
            word_num1 = text_sentence["start_word_num"]
            word_num2 = text_sentence["end_word_num"]
            self.do_not_pronounce_next = True
            self.select_word_num(word_num1)
            self.select_word_num(word_num2)

    def open_url(self, url):
        """Open URL in open tab, only works for macOS"""
        if (
            platform.system() == "Darwin"
            and self.open_urls_in_same_tab
            and self.has_opened_new_browser_tab
        ):
            script = """tell application "Google Chrome"
                            tell front window
                                set URL of active tab to "%s"
                            end tell
                        end tell """ % url.replace(
                '"', "%22"
            )
            osapipe = os.popen("osascript", "w")
            if osapipe is None:
                return False

            osapipe.write(script)
            rc = osapipe.close()
            return not rc
        else:  # Open URL in new tab
            webbrowser.open(url)
            self.has_opened_new_browser_tab = True

    def open_external_resource(self, pressed_key, lemma=False):
        if self.language in self.config["languages"]:
            resources = self.config["languages"][self.language].get(
                "external_resources"
            )
            if not resources:
                return
        common_resources = self.config.get("common_external_resources")
        if common_resources:
            resources += common_resources

        resource_found = False
        for resource in resources:
            if pressed_key.lower() == resource.get("open_key"):
                resource_found = True
                url = resource.get("url")
                phrase_word_delimiter = resource.get("phrase_word_delimiter")
        if not resource_found:
            return

        url_parts = url.split("%s")
        if not len(url_parts) == 2:
            error_string = (
                "Could not open the external resource due to incorrect formating. "
                + f"The url {url} should contain exactly one %s as a word placeholder."
            )
            print(error_string)
            return

        if lemma:
            lookup_text = None
            if self.active_looked_up and "lemmas" in self.active_info:
                lemmas = self.active_info["lemmas"]
                if len(lemmas) > 0:
                    lookup_text = list(lemmas)[0]
        else:
            lookup_text = None
            if self.active_phrase:
                if phrase_word_delimiter:
                    lookup_text = phrase_word_delimiter.join(
                        self.active_phrase["words"]
                    )
            elif self.active_word_num:
                lookup_text = self.get_active_word()

        if lookup_text:
            url = url_parts[0] + lookup_text + url_parts[1]
            self.open_url(url)


class SideFieldTitle(QLabel):
    def __init__(self, text, styling):
        super().__init__(text)
        self.styling = styling
        self.setMaximumWidth(self.styling["side_field_max_width"])

        background = self.styling["colors"]["field_title_background"]
        text_color = self.styling["colors"]["field_title_text"]
        title_style = self.styling["side_field_title"]
        padding = self.styling["side_field_title_padding"]

        style_sheet = (
            "QLabel {background-color: "
            + background
            + "; "
            + "color: "
            + text_color
            + "; "
            + "font-family: "
            + str(title_style["font"])
            + "; "
            + "font-size: "
            + str(title_style["size"])
            + "px; "
            + "padding: "
            + str(padding)
            + "px;}"
        )
        if title_style["bold"]:
            style_sheet += "QLabel {font-weight: bold; }"
        if title_style["italic"]:
            style_sheet += "QLabel {font-style: italic; }"
        self.setStyleSheet(style_sheet)
