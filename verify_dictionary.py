import sys
import os
import django

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zeno.settings")
django.setup()

from services.ai_dictionary_service import AiDictionaryService
from django.conf import settings


def test_dictionary_service():
    print("Testing AiDictionaryService...")
    print(f"Mock Mode: {getattr(settings, 'MOCK_AI_DICTIONARY', False)}")

    service = AiDictionaryService()

    word = "production"
    print(f"Defining word: {word}")
    result = service.define_word(word)

    if result:
        print("\nResult:")
        print(f"Word: {result.get('word')}")
        print(f"Definition: {result.get('definition')}")
        print(f"IPA: {result.get('ipa')}")
        print("\nSamples:")
        for sample in result.get("samples", []):
            print(f"- EN: {sample.get('text')}")
            print(f"  VI: {sample.get('vietnamese_text')}")
            print(f"  Audio: {sample.get('audio_link')}")
    else:
        print("Failed to get response (check logs for errors).")


if __name__ == "__main__":
    test_dictionary_service()
