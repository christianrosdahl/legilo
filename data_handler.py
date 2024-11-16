import os
import pickle


class DataHandler:
    def __init__(self, data_dir, language):
        self.data_dir = data_dir
        self.language = language

        self.known_words = {}
        self.learning_words = {}
        self.ignored_words = []
        self.phrases = {}
        self.last_opened_files = []

        self.load()

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
        self.ignored_words.append(word)

    def remove_word(self, word):
        """Remove word from data"""
        if word in self.ignored_words:
            self.ignored_words.remove(word)
        elif word in self.learning_words:
            del self.learning_words[word]
        elif word in self.known_words:
            del self.known_words[word]

    def add_to_phrases(self, info):
        phrase_words = info["phrase_words"]
        if not self.is_in_phrases(phrase_words):
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
            self.phrases = self.load_from_history("phrases")
        except:
            self.phrases = {}

    def save(self):
        """Save all the word lists and current state"""
        self.save_to_history(self.known_words, "known_words")
        self.save_to_history(self.learning_words, "learning_words")
        self.save_to_history(self.ignored_words, "ignored_words")
        self.save_to_history(self.phrases, "phrases")
        self.save_to_history(self.last_opened_files, "last_opened_files")

        print(f"Number of known words: {len(self.known_words)}")

    def save_as_txt(self):
        """Save all the word lists as txt files"""
        self.save_list_as_txt(self.known_words, "known_words")
        self.save_list_as_txt(self.learning_words, "learning_words")
        self.save_list_as_txt(self.ignored_words, "ignored_words")
        self.save_list_as_txt(self.learning_words.keys(), "learning_words_list")
        self.save_list_as_txt(self.phrases, "phrases")

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

    def save_to_txt(self, title, text, file_name, directory):
        """Save to .txt file"""
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        file = open(directory + "/" + file_name, "w")
        file.write(title)
        file.write("\n")
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

    def save_list_as_txt(self, obj, name):
        """Save word list as txt file"""
        self.save_to_txt(
            name,
            str(obj),
            name + ".txt",
            self.data_dir + "/" + self.language + "/" + "txt_word_lists",
        )
