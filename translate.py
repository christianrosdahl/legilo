import os
import re
import unicodedata
import warnings

import requests
import stanza
from bs4 import BeautifulSoup
from googletrans import Translator

from gpt_translator import GPTTranslator
from language_code import get_language_code
from remove_pronunciation_accents import remove_pronunciation_accents


# Ignore warnings from and related to stanza
warnings.filterwarnings(
    "ignore", category=UserWarning, module="torch._weights_only_unpickler"
)
warnings.filterwarnings(
    "ignore", category=UserWarning, module="stanza.models.common.pretrain"
)
warnings.filterwarnings(
    "ignore",
    message=(
        "The saved constituency parser has an old format using Enum, set, "
        + "unsanitized Transitions.*"
    ),
    module="stanza.models.constituency.base_trainer",
)
warnings.filterwarnings(
    "ignore",
    message=(
        "The saved classifier has an old format using SimpleNamespace and/or Enum "
        + "instead of a dict to store config.*"
    ),
    module="stanza.models.classifiers.trainer",
)


# Define parts of speech
PARTS_OF_SPEECH = [
    "noun",
    "verb",
    "adjective",
    "adverb",
    "determiner",
    "article",
    "preposition",
    "conjunction",
    "proper noun",
    "letter",
    "character",
    "phrase",
    "proverb",
    "idiom",
    "symbol",
    "syllable",
    "numeral",
    "initialism",
    "interjection",
    "definitions",
    "pronoun",
]


class LegiloTranslator:
    def __init__(
        self,
        language,
        use_lemma=True,
        lemmatizer_dir=None,
        machine_translator=None,
        dest_language="English",
    ):
        self.language = language.capitalize()
        self.dest_language = dest_language.capitalize()
        if not machine_translator:
            machine_translator == "Google"
        if machine_translator == "Google":
            self.google_translator = Translator()
        elif machine_translator == "GPT":
            self.gpt_translator = GPTTranslator(self.language, self.dest_language)
        if self.language == "Croatian":
            self.language = "Serbo-Croatian"  # Used in Wiktionary
        self.use_lemma = use_lemma
        self.machine_translator = machine_translator
        if use_lemma:
            print(
                "Loading models for finding dictionary forms of words to look up (lemmatizer).\n"
                + "This might take a while, especially the first time for a new language, "
                + "since the models must be downloaded."
            )
            if lemmatizer_dir:
                if not os.path.exists(lemmatizer_dir):
                    os.makedirs(lemmatizer_dir)
                self.nlp = stanza.Pipeline(
                    get_language_code(language),
                    lemmatizer_dir,
                    download_method=stanza.DownloadMethod.REUSE_RESOURCES,
                    verbose=False,
                )
            else:
                self.nlp = stanza.Pipeline(
                    get_language_code(language),
                    download_method=stanza.DownloadMethod.REUSE_RESOURCES,
                    verbose=False,
                )
            print("The models were loaded.")
        else:
            self.nlp = None

    def translate(
        self,
        word,
        machine_trans="auto",
        is_phrase=False,
        lemmas=None,
        machine_trans_item=None,
    ):
        input_lemmas = lemmas
        lemmas = set()
        words_parsed_from_wiktionary = set()
        word = remove_pronunciation_accents(self.language, word)
        word = unicodedata.normalize("NFC", word)
        results, wiktionary_lemmas = self.parse_from_wiktionary(word)
        words_parsed_from_wiktionary.add(word)
        lemmas |= wiktionary_lemmas

        # Handle that nouns must be looked up with capital letter in German
        if self.language == "German" and len(word) > 0:
            if len(word) == 1:
                capitalized_word = word.upper()
            else:
                capitalized_word = word[0].upper() + word[1:]
            capitalized_results, wiktionary_lemmas = self.parse_from_wiktionary(
                capitalized_word
            )
            words_parsed_from_wiktionary.add(capitalized_word)
            results += capitalized_results
            lemmas |= wiktionary_lemmas

        if input_lemmas != None:
            lemmas = input_lemmas

        lemmas = {unicodedata.normalize("NFC", lemma) for lemma in lemmas}
        for lemma in lemmas:
            if lemma not in words_parsed_from_wiktionary:
                results += self.parse_from_wiktionary(lemma)[0]
                words_parsed_from_wiktionary.add(lemma)

        # Find lemmas using NLP model
        if input_lemmas == None and self.use_lemma and not is_phrase:
            nlp_lemma = self.get_lemma(word).lower()
            lookup_words_from_result = self.get_lookup_words_from_results(results)
            if (
                nlp_lemma not in lemmas
                and nlp_lemma != word.lower()
                and nlp_lemma not in lookup_words_from_result
            ):
                nlp_lemma = unicodedata.normalize("NFC", nlp_lemma)
                if nlp_lemma not in words_parsed_from_wiktionary:
                    wiktionary_res = self.parse_from_wiktionary(nlp_lemma)[0]
                    words_parsed_from_wiktionary.add(nlp_lemma)
                if len(wiktionary_res) > 0:
                    results += wiktionary_res
                    lemmas.add(nlp_lemma)

        # If the word wasn't found in Wiktionary, add a machine translation first.
        # This is the default behavior, for machine_trans == 'auto'.
        # If machine_trans == True, a machine translation is added anyway.
        # If machine_trans == False, no machine translation is added.
        result_sources = self.get_sources_from_results(results)
        if (
            machine_trans == "auto" and "Wiktionary" not in result_sources
        ) or machine_trans == True:
            if not machine_trans_item:
                machine_trans_item = self.get_machine_translation(word)[0]
            results += [machine_trans_item]

        if input_lemmas == None and machine_trans_item:
            lemma = self.get_lemma_from_machine_trans(machine_trans_item)
            if lemma and lemma != word.lower():
                lemmas.add(lemma)

        lemmas = {unicodedata.normalize("NFC", lemma) for lemma in lemmas}
        for lemma in lemmas:
            if lemma not in words_parsed_from_wiktionary:
                results += self.parse_from_wiktionary(lemma)[0]
                words_parsed_from_wiktionary.add(lemma)

        return results, lemmas

    def get_info(
        self,
        word,
        include_word_info=True,
        include_etymology=True,
        include_machine_trans="auto",
        is_phrase=False,
        word_lemmas=None,
        machine_trans_item=None,
    ):
        """Get word info, including translation, on the format used in Legilo"""
        remark_line_marker = "\u2022 "
        translation, lemmas = self.translate(
            word,
            is_phrase=is_phrase,
            machine_trans=include_machine_trans,
            lemmas=word_lemmas,
            machine_trans_item=machine_trans_item,
        )
        wordtypes = set()
        genders = set()
        remarks = []
        etymologies = []
        for i, item in enumerate(translation):
            if "part_of_speech" in item:
                wordtypes.add(item["part_of_speech"])
            if "gender" in item:
                gender_string_parts = item["gender"].split()
                if "m" in gender_string_parts:
                    genders.add("m")
                if "f" in gender_string_parts:
                    genders.add("f")
                if "n" in gender_string_parts:
                    genders.add("n")
                if "c" in gender_string_parts:
                    genders.add("c")
            if "word_info" in item and include_word_info:
                if "word" in item:
                    remark_line = (
                        remark_line_marker + item["word"] + ": " + item["word_info"]
                    )
                    if not remark_line in remarks:  # Avoid duplicates
                        remarks.append(remark_line)
                else:
                    remarks.append(remark_line_marker + item["word_info"])
            if "etymology" in item:
                etymologies.append(
                    remark_line_marker + f"Etymology {i+1}: " + item["etymology"]
                )
        info = {"dict_word": word, "trans": translation}
        if len(wordtypes) > 0:
            info["word_type"] = ", ".join(wordtypes)
        if len(genders) > 0:
            info["gender"] = ", ".join(genders)
        info["lemmas"] = lemmas
        if include_etymology and len(etymologies) > 0:
            remarks += etymologies
        if len(remarks) > 0:
            info["remark"] = "\n".join(remarks)
        return info

    def get_lemma(self, word):
        """
        Get the dictionary form (lemma) of a given word.
        """
        doc = self.nlp(word)
        lemma = doc.sentences[0].words[0].lemma
        lemma = unicodedata.normalize("NFC", lemma)
        return lemma

    def get_lemma_from_machine_trans(self, machine_trans_item):
        if not "definitions" in machine_trans_item:
            return None
        definition = machine_trans_item["definitions"][0]["definition"]
        if not ":" in definition:
            return None
        lemma = definition.split(":")[0]
        if len(lemma) == 0:
            return None
        lemma = unicodedata.normalize("NFC", lemma)
        return lemma

    def extract_first_parentheses_content(self, s):
        # Regular expression to find content within parentheses
        pattern = r"\((.*?)\)"
        # Search for the first match in the string
        match = re.search(pattern, s)
        # Return the matched content if found, otherwise return None
        return match.group(1) if match else None

    def find_lemma_after_of(self, string):
        words = string.split()
        for i, word in enumerate(words):
            if word == "of" and i < len(words) - 1:
                return words[i + 1]
        return None

    def get_lookup_words_from_results(self, results):
        words = set()
        for item in results:
            if "word" in item:
                words.add(item["word"].lower())
        return words

    def get_sources_from_results(self, results):
        sources = set()
        for item in results:
            if "source" in item:
                sources.add(item["source"])
        return sources

    def get_google_translation(self, word):
        try:
            trans = self.google_translator.translate(
                word,
                src=get_language_code(self.language),
                dest=get_language_code(self.dest_language),
            ).text
        except:
            trans = "[Google Translate error]"
        if trans == word:
            trans = "?"
        results = [
            {
                "word": word,
                "definitions": [{"definition": trans}],
                "source": "Google Translate",
            }
        ]
        return results

    def get_gpt_translation(self, word):
        trans = "?"
        base_form = word
        num_words = len(word.split())
        try:
            result = self.gpt_translator.translate(word)
            if "error" in result:
                trans = result["error"]
            elif num_words == 1:
                if "translations" in result:
                    trans = ", ".join(result["translations"])
                else:
                    trans = "?"
                base_form = result["base_form"]
                num_words = len(word.split())
                if num_words == 1 and base_form != word:
                    if trans == "?":
                        trans = base_form
                    else:
                        trans = base_form + ": " + trans
            else:
                trans = result["translation"]
            if len(trans) == 0:
                trans = "?"
        except:
            trans = "[GPT translator error]"
        results = [
            {
                "word": base_form,
                "definitions": [{"definition": trans}],
                "source": "GPT",
            }
        ]
        return results

    def get_machine_translation(self, word):
        if self.machine_translator == "GPT":
            return self.get_gpt_translation(word)
        else:  # self.machine_translator == "Google"
            return self.get_google_translation(word)

    def parse_from_wiktionary(self, word):
        lemmas = set()

        url = f"https://en.wiktionary.org/wiki/{word}"
        response = None
        try:
            response = requests.get(url, timeout=10)
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred: {req_err}")
        except Exception as general_err:
            print(f"An unexpected error occurred: {general_err}")

        if not response or response.status_code != 200:
            return [], lemmas

        soup = BeautifulSoup(response.content, "html.parser")

        # Remove all <link> tags, while keeping their content
        for link_tag in soup.find_all("link"):
            link_tag.unwrap()

        # Find the section for the current language
        language_sections = soup.find_all("div", class_="mw-heading2")
        current_language_section = None
        for language_section in language_sections:
            current_language_section = language_section.find("h2", id=self.language)
            if current_language_section:
                break
        if not current_language_section:
            return [], lemmas
        # Extract the content under the current language section until the next h2 tag
        content = []
        current_element = language_section.find_next_sibling()
        while current_element and not current_element.find("h2"):
            content.append(current_element)
            current_element = current_element.find_next_sibling()

        results = []

        found_word = False
        look_for_etymology = False
        found_etymology = None
        for element in content:
            if look_for_etymology and element.name == "div":
                look_for_etymology = False
            if self.is_etymology(element):
                look_for_etymology = True
            elif look_for_etymology and element.name == "p":
                found_etymology = element.text.strip()
                look_for_etymology = False
            elif self.is_word_heading(element):
                results.append(
                    {
                        "part_of_speech": self.get_part_of_speech(element),
                        "definitions": [],
                        "source": "Wiktionary",
                    }
                )
                found_word = True
                if found_etymology:
                    results[-1]["etymology"] = found_etymology
                    found_etymology = None
            elif element.name == "p" and element.find("span", class_="headword-line"):
                # Extract headword line
                headword_line = element.find("span", class_="headword-line").text
                word_info = self.extract_first_parentheses_content(headword_line)
                if found_word and word_info:
                    results[-1]["word_info"] = word_info
                # Extract headword
                if found_word and element.find("strong", class_="headword"):
                    headword = element.find("strong", class_="headword").text
                    results[-1]["word"] = remove_pronunciation_accents(
                        self.language, headword
                    )
                # Extract gender if available
                gender_tag = element.find("span", class_="gender")
                if found_word and gender_tag:
                    results[-1]["gender"] = gender_tag.text.strip()
                # Exctract qualifier if available
                qualifier_tag = element.find("span", class_="qualifier-content")
                if found_word and qualifier_tag:
                    results[-1]["qualifier"] = qualifier_tag.text.strip()
            elif element.name == "ol":
                # Extract definitions
                for li in element.find_all("li", recursive=False):
                    definition_entry = {}
                    synonyms = li.find("span", class_="synonym")
                    if synonyms:
                        definition_entry["synonyms"] = synonyms.text.replace(
                            "Synonyms: ", ""
                        ).replace("Synonym: ", "")
                    antonyms = li.find("span", class_="antonym")
                    if antonyms:
                        definition_entry["antonyms"] = antonyms.text.replace(
                            "Antonyms: ", ""
                        ).replace("Antonym: ", "")
                    # Remove the unwanted tags
                    for tag in li.find_all(["dl", "div", "ul"]):
                        tag.decompose()
                    definition_text = li.text.strip()
                    definition_text = definition_text.replace("\n\n", "\n")
                    definition_text = definition_text.replace("\n", " \n    \u2022 ")
                    definition_entry["definition"] = definition_text
                    lemma = self.get_lemma_from_def(definition_text)
                    if lemma:
                        lemmas.add(lemma)
                        if found_word:
                            results[-1]["lemma"] = lemma

                    if found_word:
                        results[-1]["definitions"].append(definition_entry)

        return results, lemmas

    def is_etymology(self, element):
        if element.name == "div" and "mw-heading" in element.get("class", []):
            header_tag = element.find(["h3", "h4"])
            if header_tag:
                header_text = header_tag.text
                if "Etymology" in header_text:
                    return True
        return False

    def is_word_heading(self, element):
        if element.name == "div" and "mw-heading" in element.get("class", []):
            header_tag = element.find(["h3", "h4"])
            if header_tag:
                header_text = header_tag.text.lower()
                if header_text in PARTS_OF_SPEECH:
                    return True
        return False

    def get_part_of_speech(self, element):
        if element.name == "div" and "mw-heading" in element.get("class", []):
            header_tag = element.find(["h3", "h4"])
            if header_tag:
                header_text = header_tag.text.lower()
                if header_text in PARTS_OF_SPEECH:
                    return header_text
        return ""

    def get_lemma_from_def(self, translation):
        triggers = [
            "first-person",
            "second-person",
            "third-person",
            "participle",
            "inflection",
            "imperfect",
            "subjunctive",
            "gerund",
            "present",
            "verbform",
            "perfective of",
            "imperfective of",
            "plural of",
            "singular of",
            "inflection of",
            "variant of",
            "female equivalent of",
            "compound of",
            "indicative of",
        ]
        lemma = None
        if any(trigger in translation for trigger in triggers) and "of" in translation:
            translation = translation.replace(":", "")
            translation = translation.replace(";", "")
            translation = translation.replace("the ", "")
            translation = translation.replace("adjective ", "")
            translation = translation.replace("verb ", "")
            translation = translation.replace("infinitive ", "")
            lemma = self.find_lemma_after_of(translation)
            if lemma:
                lemma = remove_pronunciation_accents(self.language, lemma)
        return lemma
