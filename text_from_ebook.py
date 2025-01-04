import ebooklib
import re
import unicodedata

from bs4 import BeautifulSoup
from ebooklib import epub
from pypdf import PdfReader
from PyQt5.QtWidgets import QFileDialog


def get_text_from_epub_or_pdf(parent_window):
    file_path, _ = QFileDialog.getOpenFileName(
        parent_window, "Open EPUB or PDF File", ".", "EPUB and PDF Files (*.epub *.pdf)"
    )

    file_ending = file_path.split(".")[-1]
    if not file_path or not file_ending in ["epub", "pdf"]:
        return None

    text = None
    if file_ending == "epub":
        text = epub_to_text(file_path)
    elif file_ending == "pdf":
        text = pdf_to_text(file_path)
    if text:
        text = clean_text(text)

    return text


def epub_to_text(epub_path):
    book = epub.read_epub(epub_path)
    text = ""
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text += soup.get_text(separator="\n")
    return text


def pdf_to_text(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        page_text = re.sub(r"\t", " ", page.extract_text())
    return "\n".join(pages)


def clean_text(text):
    text = replace_ligatures(text)
    text = merge_split_words(text)
    text = remove_superfluous_newlines(text)
    return text


def replace_ligatures(text):
    return "".join(
        (
            unicodedata.normalize("NFKD", char)
            if "LATIN" in unicodedata.name(char, "")
            else char
        )
        for char in text
    )


def merge_split_words(text):
    lines = text.split("\n")
    for i in range(len(lines) - 1):
        if lines[i].endswith("-") and lines[i + 1]:
            rest_of_word = lines[i + 1].split()[0]
            lines[i] = lines[i][:-1] + rest_of_word
            lines[i + 1] = lines[i + 1].lstrip(rest_of_word).lstrip()
    return "\n".join(lines)


def remove_superfluous_newlines(text):
    # Replace three or more consecutive newlines with just two
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove newlines at the beginning and end of the text
    text = text.strip("\n")
    return text
