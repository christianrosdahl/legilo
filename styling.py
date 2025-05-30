import platform

from PyQt5.QtGui import QFontDatabase


def get_styling(config, dark_mode=False):
    font = "Helvetica Neue"  #'Avenir', 'Museo Sans Rounded', 'Bookman', 'Georgia'
    if "font" in config:
        font = config["font"]
    font = get_available_font(font, default_font="Helvetica")

    font_size = 18
    if "font_size" in config:
        font_size = config["font_size"]
    side_field_title_font_size = font_size - 4
    if platform.system() in ["Linux", "Windows"]:
        font_size -= 6

    default_colors = {
        "text_color": "black",
        "text_autocomplete_color": "darkgray",
        "text_background": "white",
        "window_background_color": "lightgray",
        "active_text": "black",
        "learning_text": "black",
        "new_text": "black",
        "known_text": "black",
        "active_background": "#fcb737",
        "learning_background": "#fde367",
        "new_background": "#cce6ff",
        "known_background": "#b0fc81",
        "phrase_mode_marker": "#A9DC76",  #'#b0fc81',
        "phrase_mode_marker_text": "black",
        "personal_translation_background": "#fcb737",
        "personal_translation_text": "black",
        "lemma_background": "#fde367",
        "lemma_text": "black",
        "machine_translation_background": "#cce6ff",
        "machine_translation_text": "black",
        "field_title_background": "darkgray",
        "field_title_text": "white",
        "gender_colors": {
            "m": "#006fd7",
            "f": "#e22200",
            "n": "#00A510",
            "c": "#5400a3",
        },
    }

    dark_mode_colors = {
        "text_color": "#F8F8F2",
        "text_autocomplete_color": "lightgray",
        "text_background": "#282c24",
        "window_background_color": "#20241c",
        "active_text": "#FD971F",
        "learning_text": "#f7d200",  #'#E6DB74',
        "new_text": "#66D9EF",
        "known_text": "#A6E22E",
        "active_background": "#403c34",
        "learning_background": "#282c24",
        "new_background": "#282c24",
        "known_background": "#282c24",
        "phrase_mode_marker": "#403c34",
        "phrase_mode_marker_text": "#A6E22E",
        "personal_translation_background": "#282c24",
        "personal_translation_text": "#FD971F",
        "lemma_background": "#282c24",
        "lemma_text": "#f7d200",
        "machine_translation_background": "#282c24",
        "machine_translation_text": "#66D9EF",
        "field_title_background": "#403c34",
        "field_title_text": "#F8F8F2",
        "gender_colors": {
            "m": "#66D9EF",
            "f": "#F92672",
            "n": "#A6E22E",
            "c": "#AE81FF",
        },
    }

    colors = default_colors
    if dark_mode:
        colors = dark_mode_colors

    styling = {
        "font": font,
        "font_size": font_size,
        "text_field_padding": 5,
        "side_field_title_padding": 5,
        "main_text_max_width": 700,
        "side_field_max_width": 500,
        "new_text_size": 14,
        "main_text": {"font": font, "size": font_size, "bold": False, "italic": False},
        "main_text_main_title": {
            "font": font,
            "size": font_size + 18,
            "bold": True,
            "italic": False,
        },
        "main_text_title": {
            "font": font,
            "size": font_size + 2,
            "bold": True,
            "italic": False,
        },
        "side_field_title": {
            "font": font,
            "size": side_field_title_font_size,
            "bold": False,
            "italic": False,
        },
        "lookup_word": {
            "font": font,
            "size": font_size + 2,
            "bold": True,
            "italic": False,
        },
        "category": {
            "font": font,
            "size": font_size - 6,
            "bold": True,
            "italic": False,
        },
        "translation": {
            "font": font,
            "size": font_size - 2,
            "bold": False,
            "italic": False,
        },
        "remark": {"font": font, "size": font_size - 4, "bold": False, "italic": False},
        "example": {"font": font, "size": font_size - 4, "bold": True, "italic": False},
        "example_translation": {
            "font": font,
            "size": font_size - 4,
            "bold": False,
            "italic": True,
        },
        "colors": colors,
    }

    return styling


def get_available_font(preferred_font, default_font="Helvetica"):
    available_fonts = QFontDatabase().families()
    if preferred_font in available_fonts:
        return preferred_font
    else:
        return default_font
