from django.http import Http404
from ninja_extra import Router

from .models import Word, WordSample
from schemas.dictionary_schemas import DictionaryResponseSchema
from services.ai_dictionary_service import AiDictionaryService

router = Router(tags=["D3votion"])
dictionary_service = AiDictionaryService()


@router.get("", response=DictionaryResponseSchema)
def search_word(request, word: str):
    """
    Get the definition, IPA, and sample sentences with audio for a word.
    Checks the database first before calling the AI service.
    """
    word_str = word.strip().lower()
    print(f"DEBUG: API received request for word='{word_str}'")

    # 1. Try to get from database first
    db_word = Word.objects.filter(word=word_str).first()
    if db_word:
        print(f"DEBUG: Found cached definition for '{word_str}' in DB.")
        samples = []
        for s in db_word.samples.all():
            samples.append(
                {
                    "text": s.text,
                    "vietnamese_text": s.vietnamese_text,
                    "audio_link": s.audio_link,
                }
            )

        return {
            "word": db_word.word,
            "definition": db_word.definition,
            "ipa": db_word.ipa,
            "samples": samples,
        }

    # 2. If not in DB, call AI service
    print(f"DEBUG: No cache for '{word_str}'. Calling AI service...")
    result = dictionary_service.define_word(word_str)

    if not result:
        print(f"DEBUG: Raising Http404 for word='{word_str}'")
        raise Http404(f"Could not find definition for word: {word_str}")

    # 3. Save to database for future use
    try:
        new_word = Word.objects.create(
            word=result["word"], definition=result["definition"], ipa=result["ipa"]
        )
        for sample in result.get("samples", []):
            WordSample.objects.create(
                word=new_word,
                text=sample["text"],
                vietnamese_text=sample["vietnamese_text"],
                audio_link=sample["audio_link"],
            )
        print(f"DEBUG: Saved definition for '{word_str}' to DB.")
    except Exception as e:
        print(f"DEBUG: Failed to save to DB: {str(e)}")

    return result
