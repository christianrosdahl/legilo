import os
import pickle
import unicodedata


class DataHandler:
    def __init__(self, data_dir, language):
        self.data_dir = data_dir
        self.language = language

        self.known_words = {}
        self.learning_words = {}
        self.ignored_words = []
        self.personal_translations = {}
        self.phrases = {}
        self.last_opened_files = []

        self.load()

        # Convert data from old format
        if len(self.personal_translations) == 0:
            self.convert_personal_translations_from_old_format()
            self.clean_lemmas_for_words()

    def add_to_known(self, word, info=None):
        """Add word to known words"""
        if word in self.ignored_words:
            self.ignored_words.remove(word)
        elif word in self.learning_words:
            del self.learning_words[word]
        self.known_words[word] = info

    def add_to_learning(self, word, info):
        """Add word to learning words"""
        if word in self.ignored_words:
            self.ignored_words.remove(word)
        elif word in self.known_words:
            del self.known_words[word]
        self.learning_words[word] = info

    def add_to_ignored(self, word):
        """Add word to ignored words"""
        if word in self.known_words:
            del self.known_words[word]
        elif word in self.learning_words:
            del self.learning_words[word]
        if word in self.personal_translations:
            del self.personal_translations[word]
        self.ignored_words.append(word)

    def add_personal_translation(self, word, personal_translation):
        """Add personal translation for word"""
        self.personal_translations[word] = personal_translation

    def remove_personal_translation(self, word):
        """Remove personal translation for word"""
        if word in self.personal_translations:
            del self.personal_translations[word]

    def remove_word(self, word):
        """Remove word from data"""
        if word in self.ignored_words:
            self.ignored_words.remove(word)
        elif word in self.learning_words:
            del self.learning_words[word]
        elif word in self.known_words:
            del self.known_words[word]
        if word in self.personal_translations:
            del self.personal_translations[word]

    def add_to_phrases(self, info):
        phrase_words = info["phrase_words"]
        if self.is_in_phrases(phrase_words):
            self.remove_from_phrases(info)
        first_word = phrase_words[0]
        if first_word in self.phrases:
            self.phrases[first_word].append(info)
        else:
            self.phrases[first_word] = [info]

    def remove_from_phrases(self, info):
        phrase_words = info["phrase_words"]
        first_word = phrase_words[0]
        if first_word in self.phrases:
            self.phrases[first_word] = [
                phrase
                for phrase in self.phrases[first_word]
                if phrase["phrase_words"] != phrase_words
            ]
        if not self.phrases[first_word]:
            del self.phrases[first_word]

    def is_in_phrases(self, phrase_words):
        first_word = phrase_words[0]
        if first_word in self.phrases:
            for phrase in self.phrases[first_word]:
                if phrase["phrase_words"] == phrase_words:
                    return True
        return False

    def get_phrase(self, phrase_words):
        first_word = phrase_words[0]
        if first_word in self.phrases:
            for phrase in self.phrases[first_word]:
                if phrase["phrase_words"] == phrase_words:
                    return phrase
        return None

    def get_all_words(self, include_translations=False, exclude_words=None):
        all_words = set()
        all_words |= self.known_words.keys()
        all_words |= self.learning_words.keys()
        all_words |= self.personal_translations.keys()
        if exclude_words:
            for word in exclude_words:
                if word in all_words:
                    all_words.remove(word)
        if include_translations:
            for word in all_words:
                if word in self.personal_translations:
                    all_words.remove(word)
                    all_words.add(word + ": " + self.personal_translations[word])
        return all_words

    def num_known_words(self):
        return len(self.known_words)

    def load(self):
        """Load all the word lists"""
        try:
            self.known_words = self.load_from_history("known_words")
        except:
            self.known_words = {}
        try:
            self.learning_words = self.load_from_history("learning_words")
        except:
            self.learning_words = {}
        try:
            self.ignored_words = self.load_from_history("ignored_words")
        except:
            self.ignored_words = []
        try:
            self.personal_translations = self.load_from_history("personal_translations")
        except:
            self.personal_translations = {}
        try:
            self.phrases = self.load_from_history("phrases")
        except:
            self.phrases = {}

    def save(self):
        """Save all the word lists and current state"""
        self.save_to_history(self.known_words, "known_words")
        self.save_to_history(self.learning_words, "learning_words")
        self.save_to_history(self.ignored_words, "ignored_words")
        self.save_to_history(self.personal_translations, "personal_translations")
        self.save_to_history(self.phrases, "phrases")
        self.save_to_history(self.last_opened_files, "last_opened_files")

    def save_as_txt(self):
        """Save all the word lists as txt files"""
        self.save_object_as_txt(self.known_words, "known_words_dict")
        self.save_object_as_txt(self.learning_words, "learning_words_dict")
        self.save_object_as_txt(
            self.personal_translations, "personal_translations_dict"
        )
        self.save_object_as_txt(self.phrases, "phrases_dict")
        self.save_list_as_txt(list(self.known_words.keys()), "known_words_list")
        self.save_list_as_txt(list(self.learning_words.keys()), "learning_words_list")
        self.save_list_as_txt(self.ignored_words, "ignored_words_list")

    def save_to_file(self, obj, name, directory):
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(directory + "/" + name + ".pkl", "wb") as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def load_from_file(self, name, directory):
        """General function for loading files"""
        with open(directory + "/" + name + ".pkl", "rb") as f:
            return pickle.load(f)

    def save_to_txt(self, text, file_name, directory):
        """Save to .txt file"""
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        file = open(directory + "/" + file_name, "w")
        file.write(text)
        file.close()

    def save_to_history(self, obj, name):
        """Save word list"""
        self.save_to_file(
            obj, name, self.data_dir + "/" + self.language + "/" + "history"
        )

    def load_from_history(self, name):
        """Load word list"""
        obj = self.load_from_file(
            name, self.data_dir + "/" + self.language + "/" + "history"
        )
        return obj

    def save_object_as_txt(self, obj, name):
        """Save word list object as txt file"""
        self.save_to_txt(
            str(obj),
            name + ".txt",
            self.data_dir + "/" + self.language + "/" + "txt_word_dicts",
        )

    def save_list_as_txt(self, list, name):
        """Save word list as txt file with one word per line"""
        self.save_to_txt(
            "\n".join(list),
            name + ".txt",
            self.data_dir + "/" + self.language + "/" + "txt_word_lists",
        )

    def convert_personal_translations_from_old_format(self):
        self.convert_old_personal_translations_from_dict(self.known_words)
        self.convert_old_personal_translations_from_dict(self.learning_words)
        self.convert_old_personal_translations_from_phrases()

    def convert_old_personal_translations_from_dict(self, dictionary):
        for word, info in dictionary.items():
            if not info:
                continue
            if not "trans" in info:
                continue
            trans = info["trans"]
            for item in trans:
                if not "source" in item or not "definitions" in item:
                    continue
                if not item["source"] == "personal translation":
                    continue
                definition = item["definitions"][0]
                if not "definition" in definition:
                    continue
                personal_trans = definition["definition"]
                self.add_personal_translation(word, personal_trans)

    def convert_old_personal_translations_from_phrases(self):
        all_phrase_infos = []
        for phrase_infos in self.phrases.values():
            all_phrase_infos += phrase_infos

        phrase_dict = {}
        for phrase_info in all_phrase_infos:
            if not "phrase_words" in phrase_info:
                continue
            phrase = " ".join(phrase_info["phrase_words"])
            phrase_dict[phrase] = phrase_info

        self.convert_old_personal_translations_from_dict(phrase_dict)

    def clean_lemmas_for_words(self):
        for dictionary in [self.known_words, self.learning_words]:
            self.clean_lemmas_for_dict(dictionary)

    def clean_lemmas_for_dict(self, dictionary):
        """
        Remove lemmas that are equal to the looked up word.
        Also make sure that the lemmas are unicode normalized, so that we don't get
        several lemmas that look the same but have different unicode representation for
        letters with accents.
        """
        for word, info in dictionary.items():
            if not info:
                continue
            if not "lemmas" in info:
                continue
            lemmas = info["lemmas"]
            lemmas = {unicodedata.normalize("NFC", lemma) for lemma in lemmas}
            word = unicodedata.normalize("NFC", word)
            if word in lemmas:
                lemmas.remove(word)
            lemmas_lower = {lemma.lower() for lemma in lemmas}
            if word.lower() in lemmas_lower:
                lemmas.remove(word)
            dictionary[word]["lemmas"] = lemmas
