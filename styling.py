def get_styling(dark_mode=False):
    font = "Helvetica Neue"  #'Avenir', 'Museo Sans Rounded', 'Bookman', 'Georgia'

    default_colors = {
        "text_color": "black",
        "text_background": "white",
        "window_background_color": "lightgray",
        "active_text": "black",
        "learning_text": "black",
        "new_text": "black",
        "known_text": "black",
        "active_background": "orange",
        "learning_background": "#fde367",
        "new_background": "#cce6ff",
        "known_background": "#b0fc81",
        "phrase_mode_marker": "#A9DC76",  #'#b0fc81',
        "phrase_mode_marker_text": "black",
        "personal_translation_background": "orange",
        "personal_translation_text": "black",
        "google_translate_background": "#A9DC76",
        "google_translate_text": "black",
        "field_title_background": "darkgray",
        "field_title_text": "white",
        "gender_colors": {"m": "blue", "f": "red", "n": "green", "c": "purple"},
    }

    dark_mode_colors = {
        "text_color": "#F8F8F2",
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
        "google_translate_background": "#282c24",
        "google_translate_text": "#A6E22E",
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

    font_size = 18

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
            "size": font_size - 4,
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
