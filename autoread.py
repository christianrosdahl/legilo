import re
import trafilatura


def autoread(url):
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        text = trafilatura.extract(downloaded)
        metadata = trafilatura.extract_metadata(downloaded)

        title = metadata.title if metadata and metadata.title else ""

        if text and title:
            lines = text.splitlines()
            first_line = lines[0].strip() if lines else ""
            if first_line == title:
                # Remove the first line (title) from text
                lines = lines[1:]
                text = "\n".join(lines).lstrip()
    else:
        print("Failed to download the webpage.")
        return "The content could not be fetched", ""

    # Replace instances of more than two newlines with exactly two newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Require title to be only one line
    title = title.replace("\n", " — ")

    # Replace single linebreaks with double linebreaks
    text = re.sub(r"(?<!\n)\n(?!\n)", "\n\n", text)

    return title, text
