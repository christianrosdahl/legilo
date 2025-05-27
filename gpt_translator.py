import os
import json
from openai import OpenAI


class GPTTranslator:
    def __init__(self, src, dest):
        self.src = src
        self.dest = dest
        # Create a client using the environment variable
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "Please set the OPENAI_API_KEY environment variable."
            )

        self.client = OpenAI(api_key=api_key)

        # Define the function (tool) schema for word translation
        self.tools_word = [
            {
                "type": "function",
                "function": {
                    "name": "translate",
                    "description": (
                        "Gets the dictionary form of a word in the source language and "
                        "translates it into the destination language."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_form": {
                                "type": "string",
                                "description": (
                                    "The base (dictionary) form of the word in the "
                                    "source language."
                                ),
                            },
                            "translations": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Translations of the base form to the destination "
                                    "language."
                                ),
                            },
                        },
                        "required": ["base_form", "translations"],
                    },
                },
            }
        ]

        # Define the function (tool) schema for phrase translation
        self.tools_phrase = [
            {
                "type": "function",
                "function": {
                    "name": "translate",
                    "description": (
                        "Translates a text from the source language into the "
                        "destination language."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "translation": {
                                "type": "string",
                                "description": (
                                    "Translation of the text to the "
                                    "destination language."
                                ),
                            },
                        },
                        "required": ["translation"],
                    },
                },
            }
        ]

    def translate(self, word: str):
        num_words = len(word.split())
        if num_words == 1:
            tools = self.tools_word
            message = (
                f'For the {self.src} word "{word}", give me the corresponding '
                "dictionary form and tranlations of the dictionary form to "
                f"{self.dest}."
            )
        else:
            tools = self.tools_phrase
            message = (
                f"Translate the following text from {self.src} (source language) to "
                f'{self.dest} (destination language): "{word}". Answer only with the '
                "translation."
            )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": message,
                    }
                ],
                tools=tools,
                tool_choice="auto",
            )

            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                return {"error": "No tool call returned."}

            arguments = json.loads(tool_calls[0].function.arguments)
            return arguments

        except Exception as e:
            return {"error": str(e)}


def run_language_lookup_loop():
    src = "Croatian"
    dest = "Swedish"
    print(f"Enter {src} words to see their base form and {dest} translations.")
    print("Type 'exit' to quit.\n")

    translator = GPTTranslator(src, dest)

    while True:
        word = input(f"{src} word: ").strip()
        if word.lower() == "exit":
            print("Goodbye!")
            break
        if not word:
            continue

        result = translator.translate(word)

        if "error" in result:
            print("Error:", result["error"])
        else:
            print(f"Base form: {result['base_form']}")
            print("Translations:", ", ".join(result["translations"]))
        print()


if __name__ == "__main__":
    run_language_lookup_loop()
