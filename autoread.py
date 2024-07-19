import requests
from bs4 import BeautifulSoup

def autoread(url):
    # Fetch the content from the URL
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch the page. Status code: {response.status_code}")
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the <article> tag
    article_tag = soup.find('article')
    if not article_tag:
        raise Exception("No article tag found on the page.")
    
    # Remove the <footer> tag from the article content
    for footer in article_tag.find_all('footer'):
        footer.decompose()
    
    # Find all tags within the article, excluding the removed footer
    text_tags = ['p', 'h2', 'h3', 'h4', 'h5', 'h6']
    article_elements = [tag.get_text() for tag in article_tag.find_all(text_tags)]
    
    # Extract the headline from the last <h1> tag before the first <p> tag
    last_h1_before_first_p = None
    for tag in article_tag.find_all(True):
        if tag.name == 'p':
            break
        if tag.name == 'h1':
            last_h1_before_first_p = tag
    
    headline = last_h1_before_first_p.get_text().strip() if last_h1_before_first_p else "No headline found"
    
    # Combine headline and article text
    article_text = "\n\n".join(article_elements).strip()
    
    return headline, article_text