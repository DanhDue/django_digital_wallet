import google.generativeai as genai
from decouple import config


def list_models():
    api_key = config("GEMINI_API_KEY", default=None)
    if not api_key:
        print("GEMINI_API_KEY not set")
        return

    genai.configure(api_key=api_key)
    print("Available models:")
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(f"- {m.name}")


if __name__ == "__main__":
    list_models()
