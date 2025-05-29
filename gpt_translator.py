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
                        f"Gets the dictionary form of a {self.src} word and provides "
                        f"its common translations into {self.dest}. "
                        "If the word is unclear, guess the most likely interpretation."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_form": {
                                "type": "string",
                                "description": (
                                    "The base (dictionary) form of the word in "
                                    f"{self.src}."
                                ),
                            },
                            "translations": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    f"Likely {self.dest} translations of the base "
                                    f"{self.src} word, even if the word is rare or "
                                    "has multiple meanings."
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
                        f"Translates a phrase or sentence from {self.src} into "
                        f"{self.dest}."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "translation": {
                                "type": "string",
                                "description": f"Accurate and natural-sounding "
                                f"{self.dest} translation of the original {self.src} "
                                "sentence.",
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
            temperature = 0.1
            top_p = 1.0
            message = (
                f"Given the {self.src} word {repr(word)}, identify its base "
                f"(dictionary) form in {self.src} and provide several common "
                f"translations into {self.dest}. "
                "If there are multiple possible meanings, list the most likely ones. "
                "If you are unsure, make a best guess based on similar words."
            )
        else:
            tools = self.tools_phrase
            temperature = 0.5
            top_p = 0.9
            message = (
                f"Translate the following sentence from {self.src} to {self.dest}: "
                f"{repr(word)}. Return only the translation, without explanation. Use "
                f"natural, idiomatic {self.dest}."
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
                temperature=temperature,
                top_p=top_p,
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
