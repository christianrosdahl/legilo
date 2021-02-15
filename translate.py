import urllib
from urllib import parse
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from googletrans import Translator
#from wiktionaryparser import WiktionaryParser
import wiktionaryparser
from translate_collins import translate_collins

usegoogleforconjugations = True
abbreviate = False
maxnumrecursions = 3

# Get 2-letter language code (ISO 639-1)
def languagecode(language):
	if language == 'french':
		return 'fr'
	elif language == 'german':
		return 'de'
	elif language == 'italian':
		return 'it'
	elif language == 'russian':
		return 'ru'
	else:
		return '?'

def removetranscription(string):
	newstring = string
	indexcount = 0
	moreparantheses = False
	index = string.find(' (')
	if index >= 0:
		moreparantheses = True
	while moreparantheses and indexcount < len(newstring):
		index2 = newstring[indexcount:].find(')') + indexcount
		if index2 < index:
			index2 = len(newstring)-1
		substring = newstring[index+1:index2]
		if not ' (' in substring and not ' ' in substring:
			if 'á' in substring or 'ó' in substring or 'é' in substring or 'ú' in substring or 'í' in substring or 'ý' in substring or len(substring) < 7:
				newstring = newstring[:index] + newstring[min(index2+1, len(newstring)):]
		indexcount = indexcount + 1
		if indexcount > len(newstring)-1:
			moreparantheses = False
		else:
			index = newstring[indexcount:].find(' (') + indexcount
			if index < indexcount:
				moreparantheses = False
	return newstring

# Get translation and word type(s)
def translate(word, language):
	remark = ""
	recursions = 0
	if language == 'russian':
		usegoogleforconjugations = False
		abbreviate = True

	# If not first recursion
	if type(word) == tuple:
		recursions = word[1]
		word = word[0]

		if recursions >= maxnumrecursions:
			return {'trans': '', 'wordtype' : '', 'remark' : '', 'etymology' : '', 'dictword' : ''}

	# Collect translations
	translations = []

	parser = wiktionaryparser.WiktionaryParser()
	if language == 'russian':
		word2 = word.replace('а́','а')
		word2 = word2.replace('е́','е')
		word2 = word2.replace('и́','и')
		word2 = word2.replace('о́','о')
		word2 = word2.replace('у́','у')
		word2 = word2.replace('ы́','ы')
		word2 = word2.replace('э́','э')
		word2 = word2.replace('ю́','ю')
		word2 = word2.replace('я́','я')
		worddata = parser.fetch(word2,language)
	else:
		worddata = parser.fetch(word,language)
		if language == 'german':
			if len(word) > 1:
				worddata2 = parser.fetch(word[0].upper()+word[1:],language)
			else:
				worddata2 = parser.fetch('',language)

	trans = ''
	wordtype = ''
	remark = ''
	dictword = word

	# Add translations
	translations = ''
	definitions = []
	for i in range(len(worddata)):
		definitions = definitions + worddata[i]['definitions']
	if language == 'german':
		for i in range(len(worddata2)):
			definitions = definitions + worddata2[i]['definitions']

	definitionslength = len(definitions)
	translations = []
	if definitionslength > 0:
		for i in range(definitionslength):
			t = definitions[i]['text']
			partofspeech = definitions[i]['partOfSpeech']
			if 'verb' in definitions[i]['partOfSpeech']:
				for j in range(len(t)):
					t[j] = t[j].replace('feminine','feminine verbform')
					t[j] = t[j].replace('plural','plural verbform')
			translations = translations + t[1:]

	for i in range(len(translations)):
		translation = translations[i]
		if len(translation) > 0:
			translation = translation.replace(';',',')
			translation = translation.replace(':','')
			translation = translation.replace('(transitive) ','')
			translation = translation.replace('(intransitive) ','')
			translation = translation.replace('(transitive, intransitive) ','')
			translation = translation.replace('(reflexive) ','(refl.) ')
			translation = translation.replace('To','to')
			translation = translation[0].lower() + translation[1:] # don't start with capital
			if translation[-1] == '.':
				translation = translation[:-1]
			translations[i] = translation

	# Get etymology
	etymology = ''
	if len(worddata) > 0:
		etymology = worddata[0]['etymology']

	# Initial collection of translations to string (will be replaced later)
	for i in translations:
		if i not in trans:
			if len(trans) > 0:
				trans = trans + "; " + i
			else:
				trans = trans + i
	
	# Add word type
	wordtypes = []
	wordforms = ''
	if definitionslength > 0:
		for i in range(definitionslength):
			currentwordtype = ''
			description = definitions[i]['text'][0]
			# Remove transcriptions for Russian:
			if language == 'russian':
				description = removetranscription(description)
			index = description.rfind('(')
			if index >= 0:
				description2 = description[:index]
			else:
				description2 = description
			partofspeech = definitions[i]['partOfSpeech']
			if 'noun' in partofspeech:
				if '\xa0m' in description2:
					currentwordtype = 'masculine '
				if '\xa0f' in description2:
					currentwordtype = 'feminine '
				if '\xa0n' in description2:
					currentwordtype = 'neuter '
				if '\xa0m or f' in description2:
					currentwordtype = 'masculine or feminine '
			if language == 'russian' and 'verb' in partofspeech:
				if '\xa0impf' in description2:
					currentwordtype = 'imperfective '
				if '\xa0pf' in description2:
					currentwordtype = 'perfective '
				if '\xa0impf or pf' in description2:
					currentwordtype = 'imperfective or perfective '
				if '\xa0pf or impf' in description2:
					currentwordtype = 'imperfective or perfective '
			currentwordtype = currentwordtype + partofspeech
			currentwordtype = currentwordtype.replace('proper ','')
			wordtypes.append(currentwordtype)

			index = description.rfind('(')
			index2 = description.rfind(')')
			if index >= 0 and index2 >= 0:
				newwordforms = description[index+1:index2]
				if not language == 'russian':
					newwordforms = newwordforms.replace('\xa0m',' m')
					newwordforms = newwordforms.replace('\xa0f',' f')
					newwordforms = newwordforms.replace('\xa0n',' n')
					newwordforms = newwordforms.replace('masculine ','')
					newwordforms = newwordforms.replace('feminine ','')
					newwordforms = newwordforms.replace('singular ','')
					newwordforms = newwordforms.replace('plural ','')
					newwordforms = newwordforms.replace('masculine and feminine','')
					newwordforms = newwordforms.replace('and ','')
				if len(wordforms) == 0:
					wordforms = newwordforms
				elif newwordforms not in wordforms:
					wordforms = wordforms + '; ' + newwordforms

				if language == 'russian':
					if ' ' not in description:
						newwordforms = ''
					if '(imperfective ' in description:
						index = description.rfind('(imperfective ')
						index2 = description[index:].find(')') + index
					if '(perfective ' in description:
						index = description.rfind('(perfective ')
						index2 = description[index:].find(')') + index
					if index >= 0 and index2 >= 0:
						newwordforms = description[index+1:index2]
					if len(wordforms) == 0:
							wordforms = newwordforms
					elif newwordforms not in wordforms:
						wordforms = wordforms + '; ' + newwordforms

	if len(wordforms) > 0:
		# if len(remark) == 0:
		# 	remark = 'Word forms: ' + wordforms
		# else:
		# 	remark = remark + '\n\n' + 'Word forms: ' + wordforms
		if len(remark) == 0:
			remark = wordforms
		else:
			remark = remark + '\n\n' + wordforms

	# If conjugated verb:
	for j, t in enumerate(wordtypes):
		t2 = t.replace('adverb','adv') # To avoid identifying 'adverb' as verb
		if 'verb' in t2 or 'participle' in t2:
			for i, tr in enumerate(translations):
				if ('first-person' in tr or 'second-person' in tr or 'third-person' in tr or 'participle' in tr 
					or 'inflection' in tr or 'imperfect' in tr or 'subjunctive' in tr or 'gerund' in tr or 'present' in tr
					or 'feminine verbform' in tr or 'plural verbform' in tr
					or 'perfective of' or 'imperfective of') and 'of ' in tr:
					index = tr.rfind('of ')
					lookupform = tr[index+3:]
					lookupform = lookupform.replace(':','')
					lookupform = lookupform.replace('the ','')
					lookupform = lookupform.replace('adjective ','')
					lookupform = lookupform.replace('verb ','')
					endindex = lookupform.rfind(' ')
					if endindex > 0:
						lookupform = lookupform[:endindex]
					if not lookupform.lower() == word.lower():
						newtrans = translate((lookupform, recursions+1), language)
					else:
						newtrans = None
					if newtrans:
						newtranslation = newtrans['trans']
						if usegoogleforconjugations:
							translator = Translator()
							google = translator.translate(word, src=languagecode(language), dest='en').text
							if not google == word:
								translations[i] = google
							else:
								translations[i] = newtranslation
						else:
							translations[i] = newtranslation
						if len(etymology) == 0: # Take etymology from dictionary word
							etymology = newtrans['etymology']
						additionalremark = ''
						if language == 'russian':
							wordtype = newtrans['wordtype']
							if 'imperfective or perfective verb' in wordtype:
								lookupform = lookupform + ' (impf/pf)'
							elif 'imperfective verb' in wordtype:
								lookupform = lookupform + ' (impf)'
							elif 'perfective verb' in wordtype:
								lookupform = lookupform + ' (pf)'
							newtransremark = newtrans['remark']
							# if 'imperfective ' in newtransremark:
							# 	index = newtransremark.find('imperfective ')
							# 	additionalremark = newtransremark[index:]
							# 	index2 = additionalremark.find('\n')
							# 	if index2 >= 0:
							# 		additionalremark = additionalremark[:index2]
							# elif 'perfective ' in newtransremark:
							# 	index = newtransremark.find('perfective ')
							# 	additionalremark = newtransremark[index:]
							# 	index2 = additionalremark.find('\n')
							# 	if index2 >= 0:
							# 		additionalremark = additionalremark[:index2]
							additionalremark = newtransremark
						if len(additionalremark) > 0:
							additionalremark = '\n\n' + additionalremark
						if len(remark) == 0:
							remark = lookupform + ' = ' + newtranslation + additionalremark
						elif newtranslation not in remark:
							remark = remark + '\n\n' + lookupform + ' = ' + newtranslation + additionalremark
					if 'conjugated verb' in wordtypes or 'imperfective verb' in wordtypes or 'perfective verb' in wordtypes:
						wordtypes[j] = wordtypes[j].replace('verb, ','')
						wordtypes[j] = wordtypes[j].replace(' verb, ','')
					else:
						if language == 'russian':
							wordtype = newtrans['wordtype']
							if 'imperfective or perfective verb' in wordtype:
								wordtypes[j] = wordtypes[j].replace('verb','imperfective or perfective verb')
							elif 'imperfective verb' in wordtype:
								wordtypes[j] = wordtypes[j].replace('verb','imperfective verb')
							elif 'perfective verb' in wordtype:
								wordtypes[j] = wordtypes[j].replace('verb','perfective verb')
						else:
							wordtypes[j] = wordtypes[j].replace('verb','conjugated verb')
						

	# If inflected noun:
	extrainfo = []
	for t in wordtypes:
		if 'noun' in t:
			for i, tr in enumerate(translations):
				if 'plural of' in tr or 'singular of' in tr or 'inflection of' in tr:
					index = tr.rfind('of ')
					dictword = tr[index+3:]
					dictword = dictword.replace(':','')
					dictword = dictword.replace('the ','')
					dictword = dictword.replace('adjective ','')
					dictword = dictword.replace('verb ','')
					endindex = dictword.rfind(' ')
					if endindex > 0:
						dictword = dictword[:endindex]
					if not dictword.lower() == word.lower():
						newtrans = translate((dictword, recursions+1), language)
					else:
						newtrans = None
					newtranslation = newtrans['trans']
					if usegoogleforconjugations:
						translator = Translator()
						google = translator.translate(word, src=languagecode(language), dest='en').text
						if not google == word:
							translations[i] = google
						else:
							translations[i] = newtranslation
					else:
						translations[i] = newtrans['trans']
					if language == 'russian':
						extrainfo.append(tr)
					if newtrans:
						if len(etymology) == 0: # Take etymology from dictionary word
							etymology = newtrans['etymology']
						if len(remark) == 0:
							remark = dictword + ' = ' + newtrans['trans']
						elif newtrans['trans'] not in remark:
							remark = remark + '\n\n' + dictword + ' = ' + newtrans['trans']
						wordtypes.insert(0,newtrans['wordtype'])
	if len(extrainfo) > 0:
		translations = extrainfo + translations

	# Variant of noun:
	extrainfo = []
	for t in wordtypes:
		if 'noun' in t:
			for i, tr in enumerate(translations):
				if 'variant of ' in tr or 'female equivalent of' in tr:
					index = tr.rfind('of ')
					dictword = tr[index+3:]
					dictword = dictword.replace(':','')
					dictword = dictword.replace('the ','')
					dictword = dictword.replace('adjective ','')
					dictword = dictword.replace('verb ','')
					endindex = dictword.rfind(' ')
					if endindex > 0:
						dictword = dictword[:endindex]
					if language == 'russian':
						extrainfo.append(tr)
					if len(remark) == 0:
						remark = tr
					elif tr not in remark:
						remark = tr + '\n\n' + remark
	if len(extrainfo) > 0:
		translations = extrainfo + translations

	# If inflected adjective:
	extrainfo = []
	for t in wordtypes:
		if 'adjective' in t:
			for i, tr in enumerate(translations):
				if 'inflection of' in tr or (('singular' in tr or 'plural' in tr) and 'of ' in tr):
					index = tr.rfind('of ')
					dictword = tr[index+3:]
					dictword = dictword.replace(':','')
					dictword = dictword.replace('the ','')
					dictword = dictword.replace('adjective ','')
					dictword = dictword.replace('verb ','')
					endindex = dictword.rfind(' ')
					if endindex > 0:
						dictword = dictword[:endindex]
					if not dictword.lower() == word.lower():
						newtrans = translate((dictword, recursions+1), language)
						if len(etymology) == 0: # Take etymology from dictionary word
							etymology = newtrans['etymology']
						newtranstrans = newtrans['trans']
						if len(newtranstrans) > 0:
							translations[i] = newtranstrans
					if language == 'russian':
						extrainfo.append(tr)
					if len(remark) == 0:
						remark = tr
					elif newtranstrans not in remark:
						remark = tr + '\n\n' + remark
	if len(extrainfo) > 0:
		translations = extrainfo + translations

	# Collect translations to string
	trans = ''
	for i in translations:
		i = i.replace('first-person singular ','')
		i = i.replace('second-person singular ','')
		i = i.replace('third-person singular ','')
		i = i.replace('first-person plural ','')
		i = i.replace('second-person plural ','')
		i = i.replace('third-person plural ','')
		i = i.replace('indicative ','')

		if i not in trans:
			if len(trans) > 0:
				trans = trans + "; " + i
			else:
				trans = trans + i

	# Collect wordtypes to string
	wordtype = ''
	for t in wordtypes:
		if t not in wordtype:
			if len(wordtype) > 0:
				wordtype = wordtype + ", " + t
			else:
				wordtype = t

	# Remove temporary marker for conjugated verbs
	remark = remark.replace('verbform ','')

	# # Translate with Collins if translation not found
	# if len(trans) == 0 and (language == 'french' or language == 'german' or language == 'italian'):
	# 	ans = translate_collins(word, language)
	# 	dictword2 = ans['dictword']
	# 	if dictword2:
	# 		if not dictword2 == word:
	# 			ans2 = translate(dictword2, language)
	# 			trans2 = ans2['trans']
	# 			if len(trans2) > 0:
	# 				if len(remark) == 0:
	# 					remark = dictword2 + ' = ' + trans2
	# 				elif newtrans not in remark:
	# 					remark = dictword2 + ' = ' + trans2 + '\n\n' + remark

	# Translate with Google if translation not found
	if len(trans) == 0:
		translator = Translator()
		trans = translator.translate(word, src=languagecode(language), dest='en').text
		if trans == word:
			trans = ''

	# Return a question mark if no translation is found
	if len(trans) == 0:
		trans = '?'

	# Remove transcriptions for Russian:
	if language == 'russian':
		trans = removetranscription(trans)

	# Add etymology to remark
	if not language == 'russian':
		if len(etymology) > 0:
			if len(remark) == 0:
				remark = etymology
			else:
				remark = remark + '\n\n' + etymology
	else: # language == 'russian'
		if len(etymology) > 0 and not etymology in remark:
			if len(remark) == 0:
				remark = etymology
			else:
				remark = remark + '\n\n' + etymology

	if abbreviate:
		abbreviations = {'singular': 'sing', 'plural': 'pl', 'nominative': 'nom', 'genitive': 'gen', 'dative': 'dat', 'accusative': 'acc', 
		'instrumental': 'instr', 'prepositional': 'prep', 'masculine': 'masc', 'feminine': 'fem'}
		for i, j in abbreviations.items():
			trans = trans.replace(i,j)

	return {'trans': trans, 'wordtype' : wordtype, 'remark' : remark, 'etymology' : etymology, 'dictword' : dictword}

# Test:
#print(translate('parler','french'))
#print(translate('trovata','italian'))
#print(translate('hauses','german'))
#print(translate('почти','russian'))
#print(translate('katt','swedish'))
