from pydantic import BaseModel, Field
from typing import List


class SampleSchema(BaseModel):
    text: str = Field(..., description="The sample sentence text")
    vietnamese_text: str = Field(
        ..., description="The Vietnamese translation of the sample sentence"
    )
    audio_link: str = Field(..., description="Link to the audio speech for this sample")


class DictionaryResponseSchema(BaseModel):
    word: str
    definition: str
    ipa: str
    samples: List[SampleSchema]
