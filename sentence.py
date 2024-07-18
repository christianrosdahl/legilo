import urllib
from bs4 import BeautifulSoup
from urllib.request import Request
from language_code import get_language_code

# Fix for urllib ---------
import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
getattr(ssl, '_create_unverified_context', None)):
	ssl._create_default_https_context = ssl._create_unverified_context
# ------------------------

# Return n example sentences
def get_sentences(word, language, n):
	is_word = True
	if ' ' in word:
		is_word = False
	if language in ['french', 'german', 'italian', 'russian', 'spanish'] and is_word:
		link = "https://www.online-translator.com/samples/" + get_language_code(language) + "-en/" + word
		link = urllib.parse.quote(link, safe='/:',)
		link = Request(link, headers={'User-Agent': 'Mozilla/5.0'})

		with urllib.request.urlopen(link) as url:
			raw_html = url.read()

		html = BeautifulSoup(raw_html, 'html.parser')

		sentences = [''] * n
		sentence_trans = [''] * n

		count = 0
		for i in html.select('span'):
			if 'class' in i.attrs:
				#print(i['class'])
				if 'samSource' in i['class']:
					sentences[count] = i.text.strip()
				elif 'samTranslation' in i['class']:
					sentence_trans[count] = i.text.strip()
					count += 1
					if count >= n:
						break
	# elif language == 'russian' and is_word:
	# 	link = "https://context.reverso.net/translation/" + language + "-english/" + word
	# 	link = urllib.parse.quote(link, safe='/:',)
	# 	link = Request(link, headers={'User-Agent': 'Mozilla/5.0'})

	# 	# with urllib.request.urlopen(link) as url:
	# 	# 	raw_html = url.read()
	# 	try:
	# 		url = urllib.request.urlopen(link)
	# 		raw_html = url.read()
	# 	except:
	# 		raw_html = ''

	# 	html = BeautifulSoup(raw_html, 'html.parser')

	# 	sentences = [''] * n
	# 	sentence_trans = [''] * n

	# 	count = 0
	# 	for i in html.select('div'):
	# 		if 'class' in i.attrs:
	# 			if 'src' in i['class'] and 'ltr' in i['class']:
	# 				text = i.text
	# 				starts_with_space = True
	# 				while len(text) > 0 and starts_with_space:
	# 					if text[0] == ' ' or text[0] == '\n':
	# 						text = text[1:]
	# 					else:
	# 						starts_with_space = False
	# 				sentences[count] = text.strip()
	# 			elif 'trg' in i['class'] and 'ltr' in i['class']:
	# 				text = i.text
	# 				starts_with_space = True
	# 				while len(text) > 0 and starts_with_space:
	# 					if text[0] == ' ' or text[0] == '\n':
	# 						text = text[1:]
	# 					else:
	# 						starts_with_space = False
	# 					sentence_trans[count] = text.strip()
	# 				count += 1
	# 				if count >= n:
	# 					break
	else:
		sentences = [''] * n
		sentence_trans = [''] * n
	return (sentences, sentence_trans)

# Return the first example sentence
def get_first_sentence(word, language):
	(s, s_trans) = get_sentences(word, language, 1)
	return (s[0], s_trans[0])