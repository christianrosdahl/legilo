import re

import requests
from bs4 import BeautifulSoup


def autoread(url):
    # Fetch the content from the URL
    response = None
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch the page. Status code: {response.status_code}"
            )
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

    if not response:
        return "The article could not be read", ""

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the <article> tag
    article_tag = soup.find("article")
    if not article_tag:
        raise Exception("No article tag found on the page.")

    # Remove the <footer> tag from the article content
    for footer in article_tag.find_all("footer"):
        footer.decompose()

    # Remove <div> tags at same level as <p> tags if not containing a <h2>
    # The purpose is to remove ads and similar within articles
    p_tags = article_tag.find_all("p")
    for p_tag in p_tags:
        # Find all sibling <div> tags and decompose them
        for sibling in p_tag.find_next_siblings():
            if sibling.name == "div" and not sibling.find(["h2"]):
                sibling.decompose()
            elif sibling.name == "p":
                break  # Stop if another <p> tag is encountered

    # Find all tags within the article, excluding the removed footer
    text_tags = ["p", "h2", "h3", "h4", "h5", "h6"]
    article_elements = [tag.get_text() for tag in article_tag.find_all(text_tags)]

    # Extract the headline from the last <h1> tag before the first <p> tag
    last_h1_before_first_p = None
    for tag in article_tag.find_all(True):
        if tag.name == "p":
            break
        if tag.name == "h1":
            last_h1_before_first_p = tag

    headline = (
        last_h1_before_first_p.get_text().strip()
        if last_h1_before_first_p
        else "No headline found"
    )

    # Combine headline and article text
    article_text = "\n\n".join(article_elements).strip()
    # Replace instances of more than two newlines with exactly two newlines
    article_text = re.sub(r"\n{3,}", "\n\n", article_text)

    # Require headline to be only one line
    headline = headline.replace("\n", " — ")

    # Replace single linebreaks with double linebreaks
    article_text = re.sub(r"(?<!\n)\n(?!\n)", "\n\n", article_text)

    return headline, article_text
