from bs4 import BeautifulSoup
import json
import requests
import stanza
import re
import unicodedata
from googletrans import Translator
from languagecode import *

# Define parts of speech
PARTS_OF_SPEECH = [
    "noun", "verb", "adjective", "adverb", "determiner",
    "article", "preposition", "conjunction", "proper noun",
    "letter", "character", "phrase", "proverb", "idiom",
    "symbol", "syllable", "numeral", "initialism", "interjection", 
    "definitions", "pronoun",
]

class LegiloTranslator():
    def __init__(self, language, use_lemma=True):
        self.language = language
        if len(language) > 1:
            self.language = language[0].upper() + language[1:]
        if self.language == 'Croatian':
            self.language = 'Serbo-Croatian'
        self.use_lemma = use_lemma
        if use_lemma:
            print('Loading models for finding dictionary forms of words to look up...')
            self.nlp = stanza.Pipeline(languagecode(language), download_method=stanza.DownloadMethod.REUSE_RESOURCES)
            print('The models were loaded.')
        else:
            self.nlp = None

    def translate(self, word):
        results = self.parse_from_wiktionary(word)
        
        # Handle that nouns must be looked up with capital letter in German
        if self.language == 'German' and len(word) > 0:
            if len(word) == 1:
                capitalized_word = word.upper()
            else:
                capitalized_word = word[0].upper() + word[1:]
            results += self.parse_from_wiktionary(capitalized_word)

        if self.use_lemma:
            lemma = self.get_lemma(word)
            lemmas_from_wiktionary = self.get_lemmas_from_results(results)
            lookup_words_from_result = self.get_lookup_words_from_results(results)
            if (lemma != word and
                not lemma in lemmas_from_wiktionary and
                not lemma in lookup_words_from_result):
                results = results + self.parse_from_wiktionary(lemma)
        
        if len(results) == 0:
            results = self.get_google_translation(word)

        # If the specific form wasn't found in Wiktionary, add traslation of this first
        if self.remove_accents(word) not in self.get_lookup_words_from_results(results):
            results = self.get_google_translation(word) + results
        
        return results
    
    # Get word info, including translation, on the format used in Legilo
    def get_info(self, word, include_etymology=True):
        translation = self.translate(word)
        wordtypes = set()
        genders = set()
        lemmas = set()
        remarks = []
        etymologies = []
        for i, item in enumerate(translation):
            if 'part_of_speech' in item:
                wordtypes.add(item['part_of_speech'])
            if 'gender' in item:
                gender_string_parts = item['gender'].split()
                if 'm' in gender_string_parts:
                    genders.add('m')
                if 'f' in gender_string_parts:
                    genders.add('f')
                if 'n' in gender_string_parts:
                    genders.add('n')
            if 'lemma' in item:
                lemmas.add(item['lemma'])
            if 'word_info' in item:
                remarks.append(item['word_info'])
            if 'etymology' in item:
                etymologies.append(f'Etymology {i+1}: ' + item['etymology'])
        info = {'dictword' : word, 'trans': translation}
        if len(wordtypes) > 0:
            info['wordtype'] = ', '.join(wordtypes)
        if len(genders) > 0:
            info['gender'] = ', '.join(genders)
        if len(lemmas) > 0:
            info['lemmas'] = lemmas
        if include_etymology and len(etymologies) > 0:
            remarks += etymologies
        if len(remarks) > 0:
            info['remark'] = '\n\n'.join(remarks)
        return info
    
    def get_lemma(self, word):
        """
        Get the dictionary form (lemma) of a given word.
        """
        doc = self.nlp(word)
        lemma = doc.sentences[0].words[0].lemma
        return lemma
    
    def extract_first_parentheses_content(self, s):
        # Regular expression to find content within parentheses
        pattern = r'\((.*?)\)'
        # Search for the first match in the string
        match = re.search(pattern, s)
        # Return the matched content if found, otherwise return None
        return match.group(1) if match else None
    
    def find_lemma_after_of(self, string):
        words = string.split()
        for i, word in enumerate(words):
            if word == 'of' and i < len(words)-1:
                return words[i+1]
        return None

    def get_lemmas_from_results(self, results):
        lemmas = set()
        for item in results:
            if 'lemma' in item:
                lemmas.add(item['lemma'])
        return lemmas
    
    def get_lookup_words_from_results(self, results):
        words = set()
        for item in results:
            if 'word' in item:
                # Words sometimes have extra accents for pronunciation
                word = self.remove_accents(item['word'])
                words.add(word)
        return words

    def get_google_translation(self, word):
        translator = Translator()
        trans = translator.translate(word, src=languagecode(self.language), dest='en').text
        if trans == word:
            trans = '?'
        results = [{'word': word, 'definitions': [{'definition': trans}], 'source': 'Google Translate'}]
        return results
    
    def parse_from_wiktionary(self, word, lookup_wiktionary_lemmas=True):
        url = f"https://en.wiktionary.org/wiki/{word}"
        response = requests.get(url)

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.content, "html.parser")

        # Find the section for the current language
        language_sections = soup.find_all('div', class_='mw-heading2')
        current_language_section = None
        for language_section in language_sections:
            current_language_section = language_section.find('h2', id=self.language)
            if current_language_section:
                break
        if not current_language_section:
            return []
        # Extract the content under the current language section until the next h2 tag
        content = []
        current_element = language_section.find_next_sibling()
        while current_element and not current_element.find('h2'):
            content.append(current_element)
            current_element = current_element.find_next_sibling()

        results = []

        found_word = False
        look_for_etymology = False
        found_etymology = None
        lemmas = set()
        for element in content:
            if look_for_etymology and element.name == 'div':
                look_for_etymology = False
            if self.is_etymology(element):
                look_for_etymology = True
            elif look_for_etymology and element.name == 'p':
                found_etymology = element.text.strip()
                look_for_etymology = False
            elif self.is_word_heading(element):
                results.append({'part_of_speech': self.get_part_of_speech(element),
                                'definitions': [], 'source': 'Wiktionary'})
                found_word = True
                if found_etymology:
                    results[-1]['etymology'] = found_etymology
                    found_etymology = None
            elif element.name == 'p' and element.find('span', class_='headword-line'):
                # Extract headword line
                headword_line = element.find('span', class_='headword-line').text
                word_info = self.extract_first_parentheses_content(headword_line)
                if found_word and word_info:
                    results[-1]['word_info'] = word_info
                # Extract headword
                if found_word and element.find('strong', class_='headword'):
                    results[-1]['word'] = element.find('strong', class_='headword').text
                # Extract gender if available
                gender_tag = element.find('span', class_='gender')
                if found_word and gender_tag:
                    results[-1]['gender'] = gender_tag.text.strip()
                # Exctract qualifier if available
                qualifier_tag = element.find('span', class_='qualifier-content')
                if found_word and qualifier_tag:
                    results[-1]['qualifier'] = qualifier_tag.text.strip()
            elif element.name == 'ol':
                # Extract definitions
                for li in element.find_all('li', recursive=False):
                    definition_entry = {}
                    synonyms = li.find('span', class_='synonym')
                    if synonyms:
                        definition_entry["synonyms"] = synonyms.text.replace('Synonyms: ','').replace('Synonym: ','')
                    antonyms = li.find('span', class_='antonym')
                    if antonyms:
                        definition_entry["antonyms"] = antonyms.text.replace('Antonyms: ','').replace('Antonym: ','')
                    # Remove the unwanted tags
                    for tag in li.find_all(['dl', 'div', 'ul']):
                        tag.decompose()
                    definition_text = li.text.strip()
                    definition_text = definition_text.replace('\n\n', '\n')
                    definition_text = definition_text.replace('\n', ' \n    \u2022 ')
                    definition_entry["definition"] = definition_text
                    lemma = self.get_lemma_from_def(definition_text)
                    if lemma:
                        lemmas.add(lemma)
                        if found_word:
                            results[-1]['lemma'] = lemma
                        
                    if found_word:
                        results[-1]['definitions'].append(definition_entry)
        
        if lookup_wiktionary_lemmas and len(lemmas) > 0:
            for lemma in lemmas:
                results_for_lemmas = self.parse_from_wiktionary(lemma, lookup_wiktionary_lemmas=False)
                results += results_for_lemmas
        return results

    def is_etymology(self, element):
        if element.name == 'div' and 'mw-heading' in element.get('class', []):
            header_tag = element.find(['h3','h4'])
            if header_tag:
                header_text = header_tag.text
                if 'Etymology' in header_text:
                    return True
        return False

    def is_word_heading(self, element):
        if element.name == 'div' and 'mw-heading' in element.get('class', []):
            header_tag = element.find(['h3','h4'])
            if header_tag:
                header_text = header_tag.text.lower()
                if header_text in PARTS_OF_SPEECH:
                    return True
        return False

    def get_part_of_speech(self, element):
        if element.name == 'div' and 'mw-heading' in element.get('class', []):
            header_tag = element.find(['h3','h4'])
            if header_tag:
                header_text = header_tag.text.lower()
                if header_text in PARTS_OF_SPEECH:
                    return header_text
        return ""
    
    def get_lemma_from_def(self, translation):
        triggers = ['first-person', 'second-person', 'third-person', 'participle', 'inflection', 'imperfect',
                    'subjunctive', 'gerund', 'present', 'verbform', 'perfective of', 'imperfective of',
                    'plural of', 'singular of', 'inflection of', 'variant of', 'female equivalent of',
                    'compound of', 'indicative of']
        lemma = None
        if any(trigger in translation for trigger in triggers) and 'of' in translation:
            translation = translation.replace(':','')
            translation = translation.replace(';','')
            translation = translation.replace('the ','')
            translation = translation.replace('adjective ','')
            translation = translation.replace('verb ','')
            translation = translation.replace('infinitive ','')
            lemma = self.find_lemma_after_of(translation)
        return lemma
    
    def remove_accents(self, input_str):
        # Normalize the string to decompose characters into base characters and combining marks
        normalized_str = unicodedata.normalize('NFD', input_str)
        # Filter out combining marks
        return ''.join(char for char in normalized_str if not unicodedata.combining(char))

# # Test
# # language = 'Spanish'
# language = 'Serbo-Croatian'
# # language = 'Russian'
# # language = 'German'
# # words = ['comerías', 'gatos', 'perro', 'estufas', 'pintado', 'agregaríamos']
# words = ['carevo', 'priča', 'ljudskim', 'vrijednostima', 'kako']
# # words = ['говоришь', 'что', 'эти']
# # words = ['kater', 'spielt', 'verursachte', 'teletubbyzurückwinker']

# t = LegiloTranslator(language)
# for word in words:
#     print(f'Result for word {word}:')
#     results = t.translate(word)

#     # Output the results as a list of dictionaries
#     print(json.dumps(results, ensure_ascii=False, indent=2))
