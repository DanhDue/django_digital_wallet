import google.generativeai as genai
import json
import logging
from django.conf import settings
from typing import List, Dict, Any, Optional
import urllib.parse

logger = logging.getLogger(__name__)


class AiDictionaryService:
    def __init__(self):
        # Use Django settings
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)
        self.mock_mode = getattr(settings, "MOCK_AI_DICTIONARY", False)

        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use models available in user's AI Studio + flash-latest
            self.model_names = [
                "gemini-3-flash",
                "gemini-3-pro",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-flash-latest",
                "gemini-2.0-flash",
                "gemini-2.0-pro",
            ]
        else:
            logger.warning(
                "GEMINI_API_KEY not found in settings. Provide it or enable MOCK_AI_DICTIONARY."
            )
            self.model_names = []

    def define_word(self, word: str) -> Optional[Dict[str, Any]]:
        if self.mock_mode or not self.api_key:
            return self._get_mock_response(word)

        return self._try_generate_content(word)

    def _try_generate_content(self, word: str) -> Dict[str, Any]:
        prompt = self._get_prompt(word)

        # Try each model until one works or we run out
        for model_name in self.model_names:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                    ),
                )

                if response and response.text:
                    return self._process_response(response.text)

            except Exception:
                # Continue up to next model for any error to be robust
                continue

        # Fallback to mock if all models fail
        print("DEBUG: All models failed. Falling back to MOCK response.")
        return self._get_mock_response(word)

    def _get_prompt(self, word: str) -> str:
        return f"""
        Provide information for the word: "{word}"
        Return the result in JSON format with the following structure:
        {{
            "word": "{word}",
            "definition": "A clear and concise definition or explanation of the word",
            "ipa": "The IPA pronunciation of the word",
            "samples": [
                {{
                    "text": "Sample sentence 1 in English using the word",
                    "vietnamese_text": "Vietnamese translation of sample sentence 1"
                }},
                {{
                    "text": "Sample sentence 2 in English using the word",
                    "vietnamese_text": "Vietnamese translation of sample sentence 2"
                }},
                {{
                    "text": "Sample sentence 3 in English using the word",
                    "vietnamese_text": "Vietnamese translation of sample sentence 3"
                }}
            ]
        }}
        Ensure the IPA is accurate and both English samples and Vietnamese translations are natural.
        """

    def _process_response(self, text: str) -> Dict[str, Any]:
        data = json.loads(text)
        # Enrich samples with audio links
        enriched_samples = []
        for sample_data in data.get("samples", []):
            # The prompt now asks for objects, but we handle strings too for robustness
            if isinstance(sample_data, str):
                text = sample_data
                vi_text = "Dịch tự động đang cập nhật..."
            else:
                text = sample_data.get("text", "")
                vi_text = sample_data.get("vietnamese_text", "")

            audio_link = self._generate_audio_link(text)
            enriched_samples.append(
                {"text": text, "vietnamese_text": vi_text, "audio_link": audio_link}
            )

        data["samples"] = enriched_samples
        return data

    def _generate_audio_link(self, text: str) -> str:
        encoded_text = urllib.parse.quote(text)
        return f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl=en&client=tw-ob"

    def _get_mock_response(self, word: str) -> Dict[str, Any]:
        return {
            "word": word,
            "definition": f"[MOCK FALLBACK] This is a simulated definition for '{word}' due to AI service limits.",
            "ipa": "/mɒk de.fɪ.nɪʃ.ən/",
            "samples": [
                {
                    "text": f"This is the first sample sentence for {word}.",
                    "vietnamese_text": f"Đây là câu ví dụ đầu tiên cho từ {word}.",
                    "audio_link": self._generate_audio_link(
                        f"This is the first sample sentence for {word}"
                    ),
                },
                {
                    "text": f"Can you use {word} in a sentence?",
                    "vietnamese_text": f"Bạn có thể sử dụng từ {word} trong một câu không?",
                    "audio_link": self._generate_audio_link(
                        f"Can you use {word} in a sentence?"
                    ),
                },
                {
                    "text": f"The word {word} is very interesting.",
                    "vietnamese_text": f"Từ {word} rất thú vị.",
                    "audio_link": self._generate_audio_link(
                        f"The word {word} is very interesting."
                    ),
                },
            ],
        }
