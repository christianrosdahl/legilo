def word_with_article(word, gender, language):
    article = get_article(word, gender, language)
    if len(article) == 0:
        return word
    space_after_article = " "
    if language == "italian" and article == "un'":
        space_after_article = ""
    return article + space_after_article + word


def get_article(word, gender, language):
    """Returns the article of a word (or an empty string if article is not unique)"""
    if language == "french":
        vowels = "aeiouyáéèéœôù"
        # If first letter isn't a vowel
        if word[0] not in vowels:
            if gender == "m":
                return "le"
            elif gender == "f":
                return "la"
            else:
                return ""
        # If first letter is a vowel
        else:
            if gender == "m":
                return "un"
            elif gender == "f":
                return "une"
            else:
                return ""
    elif language == "german":
        if gender == "m":
            return "der"
        elif gender == "f":
            return "die"
        elif gender == "n":
            return "das"
        else:
            return ""
    elif language == "spanish":
        if gender == "m":
            return "el"
        elif gender == "f":
            return "la"
        else:
            return ""
    elif language == "swedish":
        if gender in ["c", "m", "f"]:
            return "en"
        elif gender == "n":
            return "ett"
        else:
            return ""
    elif language == "italian":
        vowels = "aeiouy"
        consonants = "bcdfghjklmnpqrstvwxz"
        if gender == "m":
            if len(word) > 0:
                if word[0] in ["x", "y", "z"]:
                    return "lo"
                if word[0] in vowels:
                    return "un"
            if len(word) > 1:
                if word[0:2] in ["gn", "pn", "ps"]:
                    return "lo"
                if word[0] == "s":
                    if word[1] in consonants:
                        return "lo"
            return "il"
        elif gender == "f":
            if len(word) > 0:
                if word[0] in vowels:
                    return "un'"
                else:
                    return "la"
        else:
            return ""
    else:
        return ""
