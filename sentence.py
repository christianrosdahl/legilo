import urllib
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from languagecode import *

# Fix for urllib ---------
import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
getattr(ssl, '_create_unverified_context', None)):
	ssl._create_default_https_context = ssl._create_unverified_context
# ------------------------

# Return n example sentences
def getsentences(word, language, n):
	isword = True
	if ' ' in word:
		isword = False
	if language == 'french' or language == 'german' or language == 'italian' and isword:
		link = "https://www.online-translator.com/samples/" + languagecode(language) + "-en/" + word
		link = urllib.parse.quote(link, safe='/:',)
		link = Request(link, headers={'User-Agent': 'Mozilla/5.0'})

		with urllib.request.urlopen(link) as url:
			raw_html = url.read()

		html = BeautifulSoup(raw_html, 'html.parser')

		sentences = [''] * n
		sentencetrans = [''] * n

		count = 0
		s = ''
		strans = ''
		for i in html.select('span'):
			if 'class' in i.attrs:
				#print(i['class'])
				if 'samSource' in i['class']:
					sentences[count] = i.text.strip()
				elif 'samTranslation' in i['class']:
					sentencetrans[count] = i.text.strip()
					count += 1
					if count >= n:
						break
	elif language == 'russian' and isword:
		link = "https://context.reverso.net/translation/" + language + "-english/" + word
		link = urllib.parse.quote(link, safe='/:',)
		link = Request(link, headers={'User-Agent': 'Mozilla/5.0'})

		# with urllib.request.urlopen(link) as url:
		# 	raw_html = url.read()
		try:
			url = urllib.request.urlopen(link)
			raw_html = url.read()
		except:
			raw_html = ''

		html = BeautifulSoup(raw_html, 'html.parser')

		sentences = [''] * n
		sentencetrans = [''] * n

		count = 0
		s = ''
		strans = ''
		for i in html.select('div'):
			if 'class' in i.attrs:
				if 'src' in i['class'] and 'ltr' in i['class']:
					text = i.text
					startswithspace = True
					while len(text) > 0 and startswithspace:
						if text[0] == ' ' or text[0] == '\n':
							text = text[1:]
						else:
							startswithspace = False
					sentences[count] = text.strip()
				elif 'trg' in i['class'] and 'ltr' in i['class']:
					text = i.text
					startswithspace = True
					while len(text) > 0 and startswithspace:
						if text[0] == ' ' or text[0] == '\n':
							text = text[1:]
						else:
							startswithspace = False
						sentencetrans[count] = text.strip()
					count += 1
					if count >= n:
						break
	else:
		sentences = [''] * n
		sentencetrans = [''] * n
	return (sentences, sentencetrans)

# Return the first example sentence
def getfirstsentence(word, language):
	(s, strans) = getsentences(word, language, 1)
	return (s[0], strans[0])