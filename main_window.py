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
    QAction,
    QComboBox,
    QDesktopWidget,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = ""
import pygame  # Play mp3 files from gtts
from googletrans import Translator

from edit_lemmas_text_field import EditLemmasTextField
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
        self.styling = get_styling(self.config, settings["dark_mode"])
        self.data = DataHandler(data_dir, language)
        self.legilo_translator = LegiloTranslator(
            language,
            use_lemma=self.config.get("use_lemmatizer"),
            lemmatizer_dir=f"{self.data_dir}/general/stanza",
        )

        # Settings
        self.save_progress = True
        self.open_urls_in_same_tab = True
        self.page_size = 1800
        self.short_text_limit = 5000
        self.autoscroll = True
        if "page_size" in self.config:
            self.page_size = self.config["page_size"]
        if "short_text_limit" in self.config:
            self.short_text_limit = self.config["short_text_limit"]
        if "autoscroll" in self.config:
            self.autoscroll = self.config["autoscroll"]

        # Get text pages
        full_text, active_word_num, page_index, page_size = self.get_text_from_file()
        self.full_text = full_text
        is_one_page_text = active_word_num != None and page_size == None
        is_short_text = len(self.full_text) <= self.short_text_limit
        if not page_index:
            page_index = 0
        if page_size:
            self.page_size = page_size
        if is_one_page_text or is_short_text:
            self.page_size = None
            self.pages = [full_text]
            page_index = 0
        else:
            self.pages = self.get_pages(self.full_text, self.page_size)
        self.text = self.pages[0]

        # State variables
        self.page_is_open = False
        self.page_index = page_index
        self.active_word_num = active_word_num
        self.active_phrase = None
        self.active_info = None
        self.active_looked_up = False
        self.editing_main_text = False
        self.editing_personal_trans = False
        self.editing_lemmas = False
        self.editing_remark = False
        self.marker_left_page_in_direction = None
        self.has_gone_through_whole_page = False
        self.phrase_selection_mode = False
        self.phrase_selection_mode_word = None
        self.selected_phrase_words = set()
        self.last_pronounced = None
        self.example_sentences = None
        self.remark_without_third_lang = None
        self.last_word_translated_to_thind_lang = None
        self.has_opened_new_browser_tab = False
        self.scrolling_in_text = False
        self.opening_page = False
        self.do_not_pronounce_next = False
        self.looking_up_new_phrase = False
        self.edit_text_after_closing_window = False
        self.last_active_word_num_with_page = None

        self.update_last_active_word_num_with_page()

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
        self.add_window_menu()

        # Set focus policy to accept keyboard input
        self.setFocusPolicy(Qt.StrongFocus)

        # Install event filter to capture key presses
        self.installEventFilter(self)

        # Connect cursor position change to highlight word by click
        self.main_text_field.cursorPositionChanged.connect(self.on_click)

        if self.settings["sound_on"]:
            pygame.mixer.init()  # Initialize mixer for playing sounds from Google TTS

        self.open_page(self.page_index)

    def open_page(self, page_index, mark_last_active=True, scroll_to_active=True):
        if self.opening_page:
            # Avoid recursion caused by self.page_selector.setCurrentIndex()
            # calling open_page()
            return
        self.opening_page = True

        if self.page_is_open:
            self.handle_active()
        self.page_index = page_index
        self.page_is_open = True
        self.marker_left_page_in_direction = None
        self.has_gone_through_whole_page = False

        self.active_word_num = None
        self.active_phrase = None
        self.active_info = None

        self.page_label.setText(f"{self.page_index + 1} of {len(self.pages)}")
        self.page_selector.setCurrentIndex(self.page_index)

        self.text = self.pages[page_index]
        is_first_page = page_index == 0
        self.insert_main_text(is_first_page)

        # Get metadata for words, sentences and phrases in text
        self.text_words = self.get_text_words()
        self.num_text_words = len(self.text_words)
        self.text_sentences = self.get_text_sentences()
        self.text_phrases = self.get_text_phrases()

        self.mark_all_words()
        self.mark_all_phrases()

        if mark_last_active and self.last_active_word_num_with_page:
            active_word_num = self.last_active_word_num_with_page["word_num"]
            last_active_page_index = self.last_active_word_num_with_page["page_index"]
            if last_active_page_index == page_index:
                first_new_word = self.get_first_new_word()
                if first_new_word and first_new_word < active_word_num:
                    active_word_num = first_new_word
                self.set_active_word_num(active_word_num)

        if scroll_to_active:
            self.scroll_to_active_word()

        self.opening_page = False

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
        self.main_layout.setMenuBar(None)
        self.menu_bar.deleteLater()
        self.menu_bar = None

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
            self.start_window.new_text(self.text_path, self.full_text)
        event.accept()

    def get_pages(self, text, page_size):
        pages = []
        lines = text.split("\n")
        page = ""
        for line in lines:
            if len(page) > 0 and len(page) + len(line) >= page_size:
                pages.append(page.strip())
                page = ""
            page += line + "\n"
        pages.append(page.strip())
        return pages

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
        self.add_navigation_bar(left_column_layout)
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
        self.lemma_text_field = EditLemmasTextField(
            self.styling, "right", "translation", 6
        )
        self.lemma_text_field.colonTyped.connect(
            lambda: self.update_lemmas(stop_editing=False)
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
        self.main_layout = main_layout

    def add_navigation_bar(self, parent):
        # Navigation row encapsulated in a widget
        navigation_widget = QWidget()
        navigation_widget.setMaximumWidth(self.styling["main_text_max_width"])
        navigation_layout = QHBoxLayout(navigation_widget)
        navigation_layout.setAlignment(Qt.AlignVCenter)

        # Label informing about the number of known words
        known_words_label_layout = QHBoxLayout()
        self.known_words_label = QLabel()
        self.known_words_label.setStyleSheet(
            f"color: {self.styling['colors']['text_color']};"
        )
        self.update_num_known_words_label()
        known_words_label_layout.addWidget(self.known_words_label)
        navigation_layout.addLayout(known_words_label_layout)

        navigation_layout.addSpacerItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Main navigation buttons for going to previous or next page
        main_navigation_buttons_layout = QHBoxLayout()

        self.prev_button = QPushButton("←")
        self.prev_button.clicked.connect(self.show_previous_page)
        main_navigation_buttons_layout.addWidget(self.prev_button)

        page_label_width = 80
        self.page_label = QLabel(f"{self.page_index + 1} of {len(self.pages)}")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setFixedWidth(page_label_width)
        self.page_label.setStyleSheet(f"color: {self.styling['colors']['text_color']};")
        main_navigation_buttons_layout.addWidget(self.page_label)

        self.next_button = QPushButton("→")
        self.next_button.clicked.connect(self.show_next_page)
        main_navigation_buttons_layout.addWidget(self.next_button)
        navigation_layout.addLayout(main_navigation_buttons_layout)

        navigation_layout.addSpacerItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Button for setting all new words on page to known and going to next page
        new_to_known_button_layout = QHBoxLayout()
        self.new_to_known_button = QPushButton("new to known + →")
        self.new_to_known_button.clicked.connect(
            self.show_next_page_and_set_new_to_known
        )
        new_to_known_button_layout.addWidget(self.new_to_known_button)
        navigation_layout.addLayout(new_to_known_button_layout)

        navigation_layout.addSpacerItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Menu for selecting any page
        self.page_selector = QComboBox()
        self.page_selector.addItems([f"Page {i+1}" for i in range(len(self.pages))])
        self.page_selector.setCurrentIndex(self.page_index)
        self.page_selector.currentIndexChanged.connect(self.open_page)
        navigation_layout.addWidget(self.page_selector)

        parent.addWidget(navigation_widget)

    def add_window_menu(self):
        menu_bar = QMenuBar(self)

        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        marked_word_menu = menu_bar.addMenu("Marked Word")
        translation_menu = menu_bar.addMenu("Translation")
        external_lookup_menu = menu_bar.addMenu("External Lookup")
        phrase_mode_menu = menu_bar.addMenu("Phrases")

        save_action = QAction("Save progress", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_data_and_active_word)

        save_as_txt_action = QAction("Save words as text files", self)
        save_as_txt_action.setShortcut("Ctrl+R")
        save_as_txt_action.triggered.connect(self.save_data_as_text_files)

        close_and_save_action = QAction("Close window and save", self)
        close_and_save_action.setShortcut("Ctrl+W")
        close_and_save_action.triggered.connect(self.close)

        close_without_saving_action = QAction("Close window without saving", self)
        close_without_saving_action.setShortcut("Ctrl+X")
        close_without_saving_action.triggered.connect(self.close_without_saving)

        close_and_edit_action = QAction("Edit text", self)
        close_and_edit_action.setShortcut("Ctrl+E")
        close_and_edit_action.triggered.connect(self.close_and_edit)

        look_up_action = QAction("Look up word", self)
        look_up_action.setShortcut(Qt.Key_Up)
        look_up_action.triggered.connect(self.look_up)

        mark_as_known_action = QAction("Mark word as known", self)
        mark_as_known_action.setShortcut(Qt.Key_Down)
        mark_as_known_action.triggered.connect(self.set_active_to_known)

        mark_as_ignored_action = QAction("Mark word as ignored", self)
        mark_as_ignored_action.setShortcut(Qt.Key_Backspace)
        mark_as_ignored_action.triggered.connect(self.set_active_to_ignored)

        pronounce_marked_word_action = QAction("Pronounce marked word", self)
        pronounce_marked_word_action.setShortcut("P")
        pronounce_marked_word_action.triggered.connect(self.pronounce_active)

        look_up_sentence_action = QAction("Translate marked word sentence", self)
        look_up_sentence_action.setShortcut("A")
        look_up_sentence_action.triggered.connect(self.look_up_current_sentence)

        edit_personal_translation_action = QAction("Edit personal translation", self)
        edit_personal_translation_action.setShortcut("I")
        edit_personal_translation_action.triggered.connect(
            self.edit_personal_translation
        )

        edit_lemmas_action = QAction("Edit lemmas for word", self)
        edit_lemmas_action.setShortcut("U")
        edit_lemmas_action.triggered.connect(self.edit_lemmas)

        edit_remark_action = QAction("Edit remark", self)
        edit_remark_action.setShortcut("R")
        edit_remark_action.triggered.connect(self.edit_remark)

        toggle_google_trans_action = QAction("Add/remove Google translation", self)
        toggle_google_trans_action.setShortcut("O")
        toggle_google_trans_action.triggered.connect(self.toggle_google_translation)

        add_third_lang_trans_action = QAction(
            "Add/remove third language translation", self
        )
        add_third_lang_trans_action.setShortcut("H")
        add_third_lang_trans_action.triggered.connect(self.add_third_lang_trans)

        ex_sentence_1_action = QAction("Select example sentence 1", self)
        ex_sentence_1_action.setShortcut("1")
        ex_sentence_1_action.triggered.connect(lambda: self.select_example_sentence(1))

        ex_sentence_2_action = QAction("Select example sentence 2", self)
        ex_sentence_2_action.setShortcut("2")
        ex_sentence_2_action.triggered.connect(lambda: self.select_example_sentence(2))

        ex_sentence_3_action = QAction("Select example sentence 3", self)
        ex_sentence_3_action.setShortcut("3")
        ex_sentence_3_action.triggered.connect(lambda: self.select_example_sentence(3))

        ex_sentence_4_action = QAction("Select example sentence 4", self)
        ex_sentence_4_action.setShortcut("4")
        ex_sentence_4_action.triggered.connect(lambda: self.select_example_sentence(4))

        ex_sentence_5_action = QAction("Select example sentence 5", self)
        ex_sentence_5_action.setShortcut("5")
        ex_sentence_5_action.triggered.connect(lambda: self.select_example_sentence(5))

        ex_sentence_6_action = QAction("Select example sentence 6", self)
        ex_sentence_6_action.setShortcut("6")
        ex_sentence_6_action.triggered.connect(lambda: self.select_example_sentence(6))

        ex_sentence_7_action = QAction("Select example sentence 7", self)
        ex_sentence_7_action.setShortcut("7")
        ex_sentence_7_action.triggered.connect(lambda: self.select_example_sentence(7))

        ex_sentence_8_action = QAction("Select example sentence 8", self)
        ex_sentence_8_action.setShortcut("8")
        ex_sentence_8_action.triggered.connect(lambda: self.select_example_sentence(8))

        ex_sentence_9_action = QAction("Use current sentence as example sentence", self)
        ex_sentence_9_action.setShortcut("9")
        ex_sentence_9_action.triggered.connect(lambda: self.select_example_sentence(9))

        ex_sentence_0_action = QAction("Remove example sentence", self)
        ex_sentence_0_action.setShortcut("0")
        ex_sentence_0_action.triggered.connect(lambda: self.select_example_sentence(0))

        phrase_mode_action = QAction("Activate/deactivate phrase selection mode", self)
        phrase_mode_action.setShortcut("E")
        phrase_mode_action.triggered.connect(self.toggle_phrase_selection_mode)

        wiktionary_lookup_action = QAction("Wiktionary", self)
        wiktionary_lookup_action.setShortcut("W")
        wiktionary_lookup_action.triggered.connect(
            lambda: self.open_external_resource("w")
        )

        google_lookup_action = QAction("Google", self)
        google_lookup_action.setShortcut("G")
        google_lookup_action.triggered.connect(lambda: self.open_external_resource("g"))

        google_images_lookup_action = QAction("Google Images", self)
        google_images_lookup_action.setShortcut("F")
        google_images_lookup_action.triggered.connect(
            lambda: self.open_external_resource("f")
        )

        wikipedia_lookup_action = QAction("Wikipedia", self)
        wikipedia_lookup_action.setShortcut("Q")
        wikipedia_lookup_action.triggered.connect(
            lambda: self.open_external_resource("q")
        )

        dictionary_lookup_action = QAction("Language-specific dictionary", self)
        dictionary_lookup_action.setShortcut("L")
        dictionary_lookup_action.triggered.connect(
            lambda: self.open_external_resource("l")
        )

        verb_lookup_action = QAction("Verb conjugation", self)
        verb_lookup_action.setShortcut("V")
        verb_lookup_action.triggered.connect(lambda: self.open_external_resource("v"))

        context_reverso_lookup_action = QAction("Context Reverso", self)
        context_reverso_lookup_action.setShortcut("C")
        context_reverso_lookup_action.triggered.connect(
            lambda: self.open_external_resource("c")
        )

        wiktionary_lookup_lemma_action = QAction("Wiktionary (Lemma)", self)
        wiktionary_lookup_lemma_action.setShortcut(Qt.ShiftModifier + Qt.Key_W)
        wiktionary_lookup_lemma_action.triggered.connect(
            lambda: self.open_external_resource("w", True)
        )

        google_lookup_lemma_action = QAction("Google (Lemma)", self)
        google_lookup_lemma_action.setShortcut(Qt.ShiftModifier + Qt.Key_G)
        google_lookup_lemma_action.triggered.connect(
            lambda: self.open_external_resource("g", True)
        )

        google_images_lookup_lemma_action = QAction("Google Images (Lemma)", self)
        google_images_lookup_lemma_action.setShortcut(Qt.ShiftModifier + Qt.Key_F)
        google_images_lookup_lemma_action.triggered.connect(
            lambda: self.open_external_resource("f", True)
        )

        wikipedia_lookup_lemma_action = QAction("Wikipedia (Lemma)", self)
        wikipedia_lookup_lemma_action.setShortcut(Qt.ShiftModifier + Qt.Key_Q)
        wikipedia_lookup_lemma_action.triggered.connect(
            lambda: self.open_external_resource("q", True)
        )

        dictionary_lookup_lemma_action = QAction(
            "Language-specific dictionary (Lemma)", self
        )
        dictionary_lookup_lemma_action.setShortcut(Qt.ShiftModifier + Qt.Key_L)
        dictionary_lookup_lemma_action.triggered.connect(
            lambda: self.open_external_resource("l", True)
        )

        verb_lookup_lemma_action = QAction("Verb conjugation (Lemma)", self)
        verb_lookup_lemma_action.setShortcut(Qt.ShiftModifier + Qt.Key_V)
        verb_lookup_lemma_action.triggered.connect(
            lambda: self.open_external_resource("v", True)
        )

        context_reverso_lookup_lemma_action = QAction("Context Reverso (Lemma)", self)
        context_reverso_lookup_lemma_action.setShortcut(Qt.ShiftModifier + Qt.Key_C)
        context_reverso_lookup_lemma_action.triggered.connect(
            lambda: self.open_external_resource("c", True)
        )

        file_menu.addAction(save_action)
        file_menu.addAction(save_as_txt_action)
        file_menu.addSeparator()
        file_menu.addAction(close_and_save_action)
        file_menu.addAction(close_without_saving_action)

        edit_menu.addAction(close_and_edit_action)

        marked_word_menu.addAction(look_up_action)
        marked_word_menu.addAction(mark_as_known_action)
        marked_word_menu.addAction(mark_as_ignored_action)
        marked_word_menu.addAction(pronounce_marked_word_action)
        marked_word_menu.addAction(look_up_sentence_action)

        translation_menu.addAction(edit_personal_translation_action)
        translation_menu.addAction(edit_lemmas_action)
        translation_menu.addAction(edit_remark_action)
        translation_menu.addAction(toggle_google_trans_action)
        translation_menu.addAction(add_third_lang_trans_action)
        translation_menu.addSeparator()
        translation_menu.addAction(ex_sentence_1_action)
        translation_menu.addAction(ex_sentence_2_action)
        translation_menu.addAction(ex_sentence_3_action)
        translation_menu.addAction(ex_sentence_4_action)
        translation_menu.addAction(ex_sentence_5_action)
        translation_menu.addAction(ex_sentence_6_action)
        translation_menu.addAction(ex_sentence_7_action)
        translation_menu.addAction(ex_sentence_8_action)
        translation_menu.addAction(ex_sentence_9_action)
        translation_menu.addAction(ex_sentence_0_action)

        phrase_mode_menu.addAction(phrase_mode_action)

        external_lookup_menu.addAction(wiktionary_lookup_action)
        external_lookup_menu.addAction(dictionary_lookup_action)
        external_lookup_menu.addAction(verb_lookup_action)
        external_lookup_menu.addAction(context_reverso_lookup_action)
        external_lookup_menu.addAction(google_lookup_action)
        external_lookup_menu.addAction(google_images_lookup_action)
        external_lookup_menu.addAction(wikipedia_lookup_action)
        external_lookup_menu.addSeparator()
        external_lookup_menu.addAction(wiktionary_lookup_lemma_action)
        external_lookup_menu.addAction(dictionary_lookup_lemma_action)
        external_lookup_menu.addAction(verb_lookup_lemma_action)
        external_lookup_menu.addAction(context_reverso_lookup_lemma_action)
        external_lookup_menu.addAction(google_lookup_lemma_action)
        external_lookup_menu.addAction(google_images_lookup_lemma_action)
        external_lookup_menu.addAction(wikipedia_lookup_lemma_action)

        self.menu_bar = menu_bar

    def show_previous_page(self):
        if self.page_index > 0:
            self.open_page(self.page_index - 1)

    def show_next_page(self):
        if self.page_index < len(self.pages) - 1:
            self.open_page(self.page_index + 1)

    def show_next_page_and_set_new_to_known(self):
        self.handle_active()
        self.has_gone_through_whole_page = True
        self.set_active_word_num(None)
        self.show_next_page()

    def update_num_known_words_label(self):
        self.known_words_label.setText(f"Known Words: {self.data.num_known_words()}")

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
        try:
            with open(self.text_path, "r") as file:
                lines = file.readlines()
                text = "".join([line for line in lines if not self.is_metadata(line)])
                text = text.strip()
                text = unicodedata.normalize("NFC", text)
                text = self.remove_line_breaks_in_paragrahs(text)
                text = self.fix_paragraph_spacing(text)
                text = self.fix_title(text)
                metadata = next(
                    (line for line in lines if self.is_metadata(line)), None
                )
                if not metadata:
                    active_word_num = None
                    page_index = None
                    page_size = None
                else:
                    metadata = metadata.strip()
                    active_word_num, page_index, page_size = self.parse_metadata(
                        metadata
                    )
                return text, active_word_num, page_index, page_size
        except Exception as e:
            self.show_error_dialog(
                "Failed to read text from file. "
                + f"The file must be a txt-file.\n\n{e}"
            )
            return "", None, None, None

    def show_error_dialog(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(message)
        error_dialog.exec_()

    def is_metadata(self, line):
        return "#METADATA" in line or "# active_word_num" in line

    def parse_metadata(self, metadata_line):
        metadata_line = metadata_line.replace("#METADATA ", "")
        metadata_line = metadata_line.replace("# ", "")
        active_word_num = None
        page_index = None
        page_size = None
        tags_and_values = metadata_line.split(", ")
        for tag_and_value in tags_and_values:
            tag_and_value = tag_and_value.split(" = ")
            if len(tag_and_value) == 2:
                tag, value = tag_and_value
                try:
                    value = int(value)
                except Exception as e:
                    value = None
                if tag == "active_word_num":
                    active_word_num = value
                elif tag == "page_index":
                    page_index = value
                elif tag == "page_size":
                    page_size = value
        return active_word_num, page_index, page_size

    def remove_line_breaks_in_paragrahs(self, text):
        """
        Remove line breaks inside of paragraphs. Only applied if the number of double
        line breaks is over a specified threshold, to handle the case when the text
        consists mainly of single-spaced paragraphs that shouldn't be merged.
        """
        min_num_double_line_breaks = 10
        num_double_line_breaks = len(re.findall(r"\n\n", text))
        if num_double_line_breaks >= min_num_double_line_breaks:
            # Replace single line breaks (not part of a double line break) with a space
            text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
        return text

    def fix_paragraph_spacing(self, text):
        """
        If all paragraphs are separated by single line breaks, they are replaced by
        double line breaks.
        """
        has_double_line_break = re.search(r"\n\n", text)
        if not has_double_line_break:
            text = re.sub(r"(?<!\n)\n(?!\n)", "\n\n", text)
        return text

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
        metadata = None
        items = []

        if len(self.full_text) == 0:
            return

        if self.last_active_word_num_with_page:
            last_active_word_num = self.last_active_word_num_with_page["word_num"]
            last_active_page_index = self.last_active_word_num_with_page["page_index"]
            items.append(f"active_word_num = {last_active_word_num}")
            if not self.page_size == None:
                items.append(f"page_index = {last_active_page_index}")
                items.append(f"page_size = {self.page_size}")
        elif not self.page_index == None and not self.page_size == None:
            items.append(f"page_index = {self.page_index}")
            items.append(f"page_size = {self.page_size}")

        if len(items) > 0:
            metadata = "#METADATA " + ", ".join(items)

        try:
            file_name = os.path.basename(self.text_path)
            self.text_path = f"{self.data_dir}/{self.language}/texts/{file_name}"
            with open(self.text_path, "w") as file:
                file.write(self.full_text)
                if metadata:
                    file.write("\n\n" + metadata)
        except Exception as e:
            print(f"An error occurred: {e}")

    def on_key_press(self, key, modifiers):
        # Close window with Cmd/Ctrl + W
        if key == Qt.Key_W and modifiers & Qt.ControlModifier:
            self.close()
            return True

        # Close window without saving for Cmd/Ctrl + X
        if key == Qt.Key_X and modifiers & Qt.ControlModifier:
            self.close_without_saving()
            return True

        # Close window, save, and edit opened text with Cmd/Ctrl + E
        if key == Qt.Key_E and modifiers & Qt.ControlModifier:
            self.close_and_edit()
            return True

        # Save data and active word with Cmd/Ctrl + S
        if key == Qt.Key_S and modifiers & Qt.ControlModifier:
            self.save_data_and_active_word()
            return True

        # Save data as text files with Cmd/Ctrl + R
        if key == Qt.Key_R and modifiers & Qt.ControlModifier:
            self.save_data_as_text_files()
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
                elif modifiers & Qt.ControlModifier:
                    self.show_next_page()
                else:
                    self.go_to_next()
            elif key == Qt.Key_Left:
                if modifiers & Qt.ShiftModifier:
                    self.go_to_previous(skip_known=False)
                elif modifiers & Qt.ControlModifier:
                    self.show_previous_page()
                else:
                    self.go_to_previous()
            elif key in [Qt.Key_Up, Qt.Key_Return]:
                if modifiers & Qt.ControlModifier:
                    if key == Qt.Key_Up:
                        self.main_text_field.scroll_up()
                    elif key == Qt.Key_Return:
                        self.show_next_page_and_set_new_to_known()
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

    def close_without_saving(self):
        reply = QMessageBox.question(
            self,
            "Close without Saving",
            "Do you really want to close without saving?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.save_progress = False
            self.close()

    def close_and_edit(self):
        self.edit_text_after_closing_window = True
        self.close()

    def save_data_and_active_word(self):
        self.data.save()
        self.save_text_with_active_word()
        print("Data and active word were saved to file.")

    def save_data_as_text_files(self):
        self.data.save_as_txt()
        print("Data was saved to text file.")

    def insert_main_text(self, is_first_page=True):
        self.editing_main_text = True
        self.main_text_field.clear()
        lines = self.text.split("\n")
        first_line = True
        for line in lines:
            if not first_line:
                line = "\n" + line
            if is_first_page and first_line:
                self.main_text_field.insert_text(
                    line, self.styling["main_text_main_title"]
                )
            else:
                if self.line_is_title(line):
                    self.main_text_field.insert_text(
                        line, self.styling["main_text_title"]
                    )
                else:
                    self.main_text_field.insert_text(line, self.styling["main_text"])
            first_line = False
        self.editing_main_text = False

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
        text = cursor.selectedText()
        text = text.replace("\u2028", " ").replace("\u2029", " ")
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

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
        self.editing_main_text = True
        cursor = self.main_text_field.textCursor()
        cursor.setPosition(start_idx)
        cursor.setPosition(end_idx, QTextCursor.KeepAnchor)
        fmt = cursor.charFormat()
        fmt.setForeground(QColor(foreground))
        fmt.setBackground(QColor(background))
        cursor.setCharFormat(fmt)
        self.editing_main_text = False

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
        self.editing_main_text = True
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
        self.editing_main_text = False

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
        if self.editing_text_field():
            return
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
        elif self.has_gone_through_whole_page:
            self.set_new_to_known(previous_word_num, self.num_text_words)
        self.update_last_active_word_num_with_page()
        self.active_info = None

        self.update_num_known_words_label()

    def update_last_active_word_num_with_page(self):
        if self.active_word_num:
            self.last_active_word_num_with_page = {
                "word_num": self.active_word_num,
                "page_index": self.page_index,
            }
        else:
            self.last_active_word_num_with_page = None

    def set_phrase_selection_mode_word(self, word_num):
        current_word_num = self.phrase_selection_mode_word
        if current_word_num and not current_word_num in self.selected_phrase_words:
            self.mark_word(current_word_num)
        self.phrase_selection_mode_word = word_num
        if word_num:
            self.mark_word(word_num, "selected")

    def on_click(self):
        """Look up clicked word and mark previous new words as known"""
        if self.editing_main_text:
            return
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

    def go_to_next(self, skip_known=True, save=True, autoscroll_if_enabled=True):
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

        if self.active_word_num and not next_word_num:
            self.marker_left_page_in_direction = "right"

        if not next_word_num:
            self.has_gone_through_whole_page = True
            if self.page_index < len(self.pages) - 1:
                self.set_active_word_num(None)
                self.open_page(self.page_index + 1, scroll_to_active=False)
                self.go_to_next(skip_known, autoscroll_if_enabled=False)
                return
        self.set_active_word_num(next_word_num)
        if self.autoscroll and autoscroll_if_enabled:
            self.scroll_to_active_word()

    def go_to_previous(self, skip_known=True, save=True, autoscroll_if_enabled=True):
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

        if self.active_word_num and not previous_word_num:
            self.marker_left_page_in_direction = "left"

        if not previous_word_num:
            if self.marker_left_page_in_direction == "left":
                if self.page_index > 0:
                    self.open_page(self.page_index - 1, mark_last_active=False)
                else:
                    self.set_active_word_num(None)
                    return

            first_new_word = self.get_first_new_word()
            if first_new_word:
                previous_word_num = first_new_word
            else:
                if skip_known:
                    last_marked_word = self.get_last_marked_word()
                    if last_marked_word:
                        previous_word_num = last_marked_word
                else:
                    previous_word_num = self.num_text_words
        self.set_active_word_num(previous_word_num)
        if self.autoscroll and autoscroll_if_enabled:
            self.scroll_to_active_word()

    def phrase_selection_next(self):
        current_word_num = self.phrase_selection_mode_word
        next_word_num = self.next_word_num(current_word_num)
        self.set_phrase_selection_mode_word(next_word_num)

    def phrase_selection_previous(self):
        current_word_num = self.phrase_selection_mode_word
        previous_word_num = self.previous_word_num(current_word_num)
        self.set_phrase_selection_mode_word(previous_word_num)

    def get_first_new_word(self):
        for word_num in range(1, self.num_text_words + 1):
            if self.is_new(self.get_word(word_num)):
                return word_num
        return None

    def get_first_marked_word(self):
        for word_num in range(1, self.num_text_words + 1):
            if self.is_marked(self.get_word(word_num)):
                return word_num
        return None

    def get_last_marked_word(self):
        for word_num in reversed(range(1, self.num_text_words + 1)):
            if self.is_marked(self.get_word(word_num)):
                return word_num
        return None

    def set_active_to_known(self):
        if self.editing_text_field():
            return
        if self.active_phrase:
            self.delete_active_phrase()
            self.active_phrase = None
            self.mark_active_word()
        elif self.active_word_num:
            self.save_active_word_as("known")
            self.go_to_next(save=False)

    def set_active_to_ignored(self):
        if self.editing_text_field():
            return
        if not self.active_phrase and self.active_word_num:
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

    def editing_text_field(self):
        return self.editing_personal_trans or self.editing_lemmas or self.editing_remark

    def edit_personal_translation(self):
        if not self.active_looked_up or self.editing_text_field():
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
        if not self.active_looked_up or self.editing_text_field():
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

    def update_lemmas(self, stop_editing=True):
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
        if stop_editing:
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
        if not self.active_looked_up or self.editing_text_field():
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
        if not self.active_looked_up or self.editing_text_field():
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
        elif not self.has_gone_through_whole_page:
            next_word_num = 1
        else:
            return None
        if next_word_num > self.num_text_words:
            self.has_gone_through_whole_page = True
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
        elif not self.has_gone_through_whole_page:
            next_word_num = 1
        else:
            return None

        while True:
            if next_word_num > self.num_text_words:
                self.has_gone_through_whole_page = True
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
        if not self.active_looked_up or self.editing_text_field():
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
        if self.editing_text_field():
            return

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
        if self.editing_text_field():
            return

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
        if self.editing_text_field():
            return

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
        if self.editing_text_field():
            return

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
