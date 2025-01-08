import os
import ssl
import urllib
from urllib.error import URLError, HTTPError
from urllib.request import Request

import requests
from bs4 import BeautifulSoup

from language_code import get_language_code

if not os.environ.get("PYTHONHTTPSVERIFY", "") and getattr(
    ssl, "_create_unverified_context", None
):
    ssl._create_default_https_context = ssl._create_unverified_context


def get_sentences(word, language, n):
    """Return n example sentences"""
    is_word = True
    if " " in word:
        is_word = False
    if language in ["french", "german", "italian", "russian", "spanish"] and is_word:
        html = None
        try:
            link = (
                "https://www.online-translator.com/samples/"
                + get_language_code(language)
                + "-en/"
                + word
            )
            link = urllib.parse.quote(
                link,
                safe="/:",
            )
            link = Request(link, headers={"User-Agent": "Mozilla/5.0"})

            with urllib.request.urlopen(link, timeout=10) as url:
                raw_html = url.read()

            html = BeautifulSoup(raw_html, "html.parser")

        except HTTPError as http_err:
            print(f"HTTP error occurred: {http_err.code} - {http_err.reason}")
        except URLError as url_err:
            print(f"URL error occurred: {url_err.reason}")
        except Exception as general_err:
            print(f"An unexpected error occurred: {general_err}")

        sentences = [""] * n
        sentence_trans = [""] * n

        if html:
            count = 0
            for i in html.select("span"):
                if "class" in i.attrs:
                    if "samSource" in i["class"]:
                        sentences[count] = i.text.strip()
                    elif "samTranslation" in i["class"]:
                        sentence_trans[count] = i.text.strip()
                        count += 1
                        if count >= n:
                            break
        return (sentences, sentence_trans)
    else:
        return get_from_glosbe(word, language, n)


def get_first_sentence(word, language):
    """Return the first example sentence"""
    (s, s_trans) = get_sentences(word, language, 1)
    return (s[0], s_trans[0])


def get_from_glosbe(word, language, n):
    url = "https://glosbe.com/" + get_language_code(language) + "/en/" + word

    response = None
    try:
        response = requests.get(url, timeout=10)
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
    except Exception as general_err:
        print(f"An unexpected error occurred: {general_err}")

    sentences = [""] * n
    sentence_trans = [""] * n

    # Check if the request was successful
    if response and response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")

        examples_div = soup.find("div", id="tmem_first_examples")

        count = 0
        if examples_div:
            # Find all <div> with class="py-2 flex" within the examples_div
            example_items = examples_div.find_all("div", class_="py-2 flex")

            for item in example_items:
                sentence_div = item.find(
                    "div",
                    class_="w-1/2 dir-aware-pr-1",
                    lang=get_language_code(language),
                )
                sentence_trans_div = item.find("div", class_="w-1/2 dir-aware-pl-1")

                if sentence_div and sentence_trans_div:
                    sentence = sentence_div.get_text().strip()
                    trans = sentence_trans_div.get_text().strip()
                    if len(sentence) < 100:
                        sentences[count] = sentence
                        sentence_trans[count] = trans
                        count += 1

                if count >= n:
                    break
    return (sentences, sentence_trans)
