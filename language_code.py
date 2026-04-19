import pycountry


def get_language_code(language_name):
    """Get 2-letter language code (ISO 639-1)"""
    language_name = language_name.lower()
    if language_name == "serbo-croatian":
        language_name = "croatian"
    if language_name == "greek":
        language_name = "Modern Greek (1453-)"
    try:
        # Look up the language code for the given language name
        language = pycountry.languages.lookup(language_name)
        return language.alpha_2
    except LookupError:
        return None
