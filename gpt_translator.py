import os
import json
from openai import OpenAI


class GPTTranslator:
    def __init__(self, src, dest):
        self.src = src.capitalize()
        self.dest = dest.capitalize()

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
                        f"Identify the dictionary (base) form of a {self.src} "
                        f"word and provide its common translations into "
                        f"{self.dest}. If the word is ambiguous, provide "
                        "translations for its most likely meanings."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_form": {
                                "type": "string",
                                "description": (
                                    f"The dictionary/base form of the word "
                                    f"in {self.src}. For nouns, use the "
                                    "dictionary form. For verbs, use the "
                                    "infinitive or equivalent dictionary form."
                                ),
                            },
                            "translations": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    f"Common {self.dest} translations of "
                                    f"the {self.src} word. Include the most "
                                    "relevant translations for its different "
                                    "common meanings."
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
                        f"Translate a phrase or sentence from {self.src} "
                        f"into natural, idiomatic {self.dest}."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "translation": {
                                "type": "string",
                                "description": (
                                    f"An accurate and natural-sounding "
                                    f"{self.dest} translation of the original "
                                    f"{self.src} sentence."
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
                f"Given the {self.src} word {repr(word)}, identify its "
                f"dictionary (base) form in {self.src} and provide several "
                f"common translations into {self.dest}. "
                "If there are multiple common meanings, include the most "
                "relevant translations. "
                "If the input is an inflected form, identify its base form. "
                "If the word is ambiguous, make the most likely "
                "interpretation based on the spelling and morphology."
            )

        else:
            tools = self.tools_phrase

            message = (
                f"Translate the following {self.src} phrase or sentence "
                f"into {self.dest}: {repr(word)}. "
                f"Use natural, idiomatic {self.dest}. "
                "Return only the translation."
            )

        try:
            response = self.client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=[
                    {
                        "role": "user",
                        "content": message,
                    }
                ],
                tools=tools,
                tool_choice="required",
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
