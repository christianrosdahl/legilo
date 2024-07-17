import urllib
from urllib import parse
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen

# Get title and text from url
def autoread(language, link):
	title = ''
	text = ''

	# Read from source
	#link2 = urllib.parse.quote(link, safe='/:',)
	#link2 = Request(link2, headers={'User-Agent': 'Mozilla/5.0'})
	link2 = link
	with urllib.request.urlopen(link2) as url:
		raw_html = url.read()
	html = BeautifulSoup(raw_html, 'html.parser')

	if language:
		if 'fr.wikipedia.org' in link:
			# Find title
			for i in html.select('h1'):
				if 'id' in i.attrs:
					if 'firstHeading' in i['id']:
						title = i.text

			# Find text
			for i in html.select('div'):
				if 'id' in i.attrs:
					if 'mw-content-text' in i['id']:
						for j in i.find_all(['p','h2','h3','h4']):
							new = j.text.replace('modifier - modifier le code','')
							new = new.replace('[modifier | modifier le code]','')
							new = new.replace('Sommaire','')
							new = new.replace('Références','')
							new = new.replace('Voir aussi','')
							new = new.replace('Liens externes','')
							if len(new) > 0:
								text = addtotext(text, new, 'text')
							

		if 'lemonde.fr' in link:
			# Find title
			for i in html.select('h1'):
				if 'class' in i.attrs:
					if 'article__title' in i['class']:
						title = i.text

			# Find description
			description = ''
			for i in html.select('p'):
				if 'class' in i.attrs:
					if 'article__desc' in i['class']:
						description = i.text
			# Remove spaces in beginning
			while len(description) > 0:
				if description[0] == ' ':
					description = description[1:]
				else:
					break
			text = addtotext(text, description, 'description')

			# Find text
			for i in html.find_all(['p','h2']):
				if 'class' in i.attrs:
					if 'article__paragraph' in i['class']:
						new = i.text
						text = addtotext(text, new, 'text')
					if 'article__sub-title' in i['class']:
						text = addtotext(text, i.text, 'text')

		if 'rfi.fr' in link:
			# Find title
			for i in html.select('h1'):
				if 'itemprop' in i.attrs:
					if 'name' in i['itemprop']:
						title = i.text

			# Find description
			for i in html.select('div'):
				if 'class' in i.attrs:
					if 'intro' in i['class']:
						text = addtotext(text, i.text, 'description')

			# Find text
			for i in html.find_all(['div']):
				if 'itemprop' in i.attrs:
					if 'articleBody' in i['class']:
						new = i.text
						text = addtotext(text, new, 'text')

		if 'lefigaro.fr' in link:
			# Find title
			for i in html.select('h1'):
				if 'class' in i.attrs:
					if 'fig-main-title' in i['class']:
						title = i.text

			# Find description
			for i in html.select('p'):
				if 'class' in i.attrs:
					if 'fig-content__chapo' in i['class']:
						text = addtotext(text, i.text, 'description')

			# Remove from text
			remove = []
			for i in html.find_all('strong'):
				remove.append(i.text)

			# Find text
			for i in html.find_all(['div']):
				if 'class' in i.attrs:
					if 'fig-content__body' in i['class']:
						for j in i.find_all(['p','h2']):
							new = j.text
							add = True
							for r in remove:
								if r in new:
									add = False
							if add: 
								text = addtotext(text, new, 'text')

		if 'spiegel.de' in link:
			remove = []
			removeifcontains = ['© SPIEGEL ONLINE 2019', 'Alle Rechte vorbehalten', 'Vervielfältigung nur mit Genehmigung', 'Im Video:']
			# Remove author info
			for i in html.select('div'):
				if 'class' in i.attrs:
					if 'author-content' in i['class']:
						remove.append(i.text)

			# Remove image captions
			for i in html.select('div'):
				if 'class' in i.attrs:
					if 'article-image-description' in i['class']:
						remove.append(i.text)

			# Find title
			for i in html.select('span'):
				if 'class' in i.attrs:
					if 'headline' in i['class']:
						title = i.text

			# Find description
			for i in html.select('p'):
				if 'class' in i.attrs:
					if 'article-intro' in i['class']:
						text = addtotext(text, i.text, 'description')

			# Find text
			for j in html.select('div'):
				if 'class' in j.attrs:
					if 'spArticleContent' in j['class']:
						subhtml = j

			for i in subhtml.find_all(['p','li']):
				if len(i.attrs) == 0:
					add = True
					for r in remove:
						if i.text in r:
							add = False
					for r in removeifcontains:
						if r in i.text:
							add = False
					if add:
						if str(i)[0:3] == '<li':
							text = addtotext(text, "- " + i.text, 'text')
						else:
							text = addtotext(text, i.text, 'text')

		if 'repubblica.it' in link:
			remove = []

			# Remove inline article
			for i in html.select('section'):
				if 'class' in i.attrs:
					if 'inline-article' in i['class']:
						remove.append(i.text)

			# Find title
			for i in html.select('h1'):
				if 'itemprop' in i.attrs:
					if 'headline' in i['itemprop']:
						title = i.text
			if len(title) == 0:
				for i in html.select('header'):
					for j in i.select('h1'):
							title = j.text

			# Find description
			for i in html.select('p'):
				if 'itemprop' in i.attrs:
					if 'description' in i['itemprop']:
						text = addtotext(text, i.text, 'description')

			# Find text
			for j in html.select('span'):
				if 'itemprop' in j.attrs:
					if 'articleBody' in j['itemprop']:
						newtext = j.text
						for r in remove:
							newtext = newtext.replace(r,'')
						text = addtotext(text, newtext, 'text')

		if 'iz.ru' in link:
			remove = []
			addnewline = []

			# Remove inline article
			for i in html.select('a'):
				if 'class' in i.attrs:
					if 'float_href_block' in i['class']:
						remove.append(i.text)

			# Remove pictures
			for i in html.select('div'):
				if 'class' in i.attrs:
					if 'slider-block2__inside__item' in i['class']:
						remove.append(i.text)

			# Add new line
			for i in html.select('p'):
				addnewline.append(i.text)
			for i in html.select('h2'):
				addnewline.append(i.text)

			# Find title
			for i in html.select('h1'):
				if 'itemprop' in i.attrs:
					if 'headline' in i['itemprop']:
						title = i.text

			# Find text
			for i in html.select('div'):
				if 'itemprop' in i.attrs:
					if 'articleBody' in i['itemprop']:
						newtext = i.text
						for r in remove:
							newtext = newtext.replace(r,'')
						for a in addnewline:
							newtext = newtext.replace(a, a + '\n\n')
						text = addtotext(text, newtext, 'text')

			# Add new lines
			# text = text + ' '
			# text = text.replace('.','*dot*')
			# text = text.replace('!','*exclamation*')
			# text = text.replace('?','*question*')
			# moredots = False
			# moreexclamations = False
			# morequestions = False
			# if text.find('*dot*') > 0:
			# 	moredots = True
			# if text.find('*exclamation*') > 0:
			# 	moreexclamations = True
			# if text.find('*question*') > 0:
			# 	morequestions = True
			# while moredots:
			# 	if not text[text.find('*dot*') + len('*dot*')] == ' ' and not text[text.find('*dot*') + len('*dot*')] == '\n' \
			# 		and not (text[text.find('*dot*') + len('*dot*')] in '0123456789' and text[text.find('*dot*')-1] in '0123456789') \
			# 		and (not text[text.find('*dot*') + len('*dot*')].lower() == text[text.find('*dot*') + len('*dot*')] or text[text.find('*dot*') + len('*dot*')] == '«'):
			# 		text = text[0:text.find('*dot*')] + '.\n\n' + text[text.find('*dot*') + len('*dot*'):]
			# 	else:
			# 		text = text[0:text.find('*dot*')] + '.' + text[text.find('*dot*') + len('*dot*'):]
			# 	if text.find('*dot*') > 0:
			# 		moredots = True
			# 	else:
			# 		moredots = False
			# while moreexclamations:
			# 	if not text[text.find('*exclamation*') + len('*exclamation*')] == ' ' and not text[text.find('*dot*') + len('*dot*')] == '\n':
			# 		text = text[0:text.find('*exclamation*')] + '!\n\n' + text[text.find('*exclamation*') + len('*exclamation*'):]
			# 	else:
			# 		text = text[0:text.find('*exclamation*')] + '!' + text[text.find('*exclamation*') + len('*exclamation*'):]
			# 	if text.find('*exclamation*') > 0:
			# 		moreexclamations = True
			# 	else:
			# 		moreexclamations = False
			# while morequestions:
			# 	if not text[text.find('*question*') + len('*question*')] == ' ' and not text[text.find('*dot*') + len('*dot*')] == '\n':
			# 		text = text[0:text.find('*question*')] + '!\n\n' + text[text.find('*question*') + len('*question*'):]
			# 	else:
			# 		text = text[0:text.find('*question*')] + '!\n\n' + text[text.find('*question*') + len('*question*'):]
			# 	if text.find('*question*') > 0:
			# 		morequestions = True
			# 	else:
			# 		morequestions = False
			if text[0] == '\n':
				text = text[1:]

			text = text.replace('\n\n\n\n\n','\n\n')
			text = text.replace('\n\n\n\n','\n\n')
			text = text.replace('\n\n\n','\n\n')


	return (title, text)

def addtotext(text, new, type):
	if not type == 'description':
		if len(text) == 0:
			return new
		else:
			return text + '\n\n' + new
	else:
		if len(text) == 0:
			return new + '\n'
		else:
			return text + '\n\n' + new + '\n'


