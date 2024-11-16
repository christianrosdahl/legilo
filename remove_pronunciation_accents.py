import re
import unicodedata


def remove_pronunciation_accents(language, input_str):
    """Remove accents added for pronunciation hints in some languages"""

    # Normalize the string to NFD (Normalization Form Decomposition)
    nfkd_form = unicodedata.normalize("NFD", input_str)

    # Define what accented letters should be kept for each language
    language = language.lower()
    letters_to_keep_accents_for = None
    if language in ["croatian", "serbo-croatian"]:
        letters_to_keep_accents_for = ["s", "c", "z"]
    elif language == "russian":
        # Remove all acute (U+0301) and grave (U+0300) accents
        return re.sub(r"[\u0300\u0301]", "", input_str)
    else:
        return input_str

    # Remove unwanted accents
    if letters_to_keep_accents_for == None:
        without_diacritics = "".join(
            c for c in nfkd_form if not unicodedata.combining(c)
        )
    else:
        new_letters = []
        for i, c in enumerate(nfkd_form):
            if not (
                unicodedata.combining(c)
                and i >= 0
                and nfkd_form[i - 1].lower() not in letters_to_keep_accents_for
            ):
                new_letters.append(c)
        without_diacritics = "".join(new_letters)
    return without_diacritics
