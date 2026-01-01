from django.db import models


class Word(models.Model):
    """
    Caches the definition and metadata for a word.
    """

    word = models.CharField(max_length=255, unique=True, db_index=True)
    definition = models.TextField()
    ipa = models.CharField(max_length=255)
    audio_downloaded = models.BooleanField(
        default=False,
        help_text="Status about whether the audio has been downloaded or not",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.word

    class Meta:
        ordering = ["word"]


class WordSample(models.Model):
    """
    Stores sample sentences associated with a Word.
    """

    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name="samples")
    text = models.TextField(help_text="The sample sentence in English")
    vietnamese_text = models.TextField(help_text="The sample sentence in Vietnamese")
    audio_link = models.URLField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sample for {self.word.word}"
