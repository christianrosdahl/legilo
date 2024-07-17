# Get 2-letter language code (ISO 639-1)
def languagecode(language):
	language = language.lower()
	if language == 'french':
		return 'fr'
	elif language == 'german':
		return 'de'
	elif language == 'italian':
		return 'it'
	elif language == 'spanish':
		return 'es'
	elif language == 'croatian' or language == 'serbo-croatian':
		return 'hr'
	elif language == 'russian':
		return 'ru'
	else:
		return '?'