import re
import unicodedata

# Arabic tashkeel (diacritics) Unicode range
_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟ]")
_TATWEEL = re.compile(r"ـ")  # kashida / tatweel ـ
_WIKI_REFS = re.compile(r"\[[^\]]{0,10}\]")  # [1], [٢], [عدل], [edit], etc.
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")

_ALEF_VARIANTS = str.maketrans("أإآٱ", "اااا")
_YA_VARIANT = str.maketrans("ى", "ي")
_TA_MARBUTA = str.maketrans("ة", "ه")


def normalize_for_search(text: str) -> str:
    """Normalize Arabic text for cache keys and search queries.

    Aggressively unifies letter variants so that queries with different
    alef/ya/tashkeel spellings produce the same key. Do NOT use for
    displayed text — it changes letters that affect meaning in display.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_ALEF_VARIANTS)
    text = text.translate(_YA_VARIANT)
    text = text.translate(_TA_MARBUTA)
    text = _TASHKEEL.sub("", text)
    text = _TATWEEL.sub("", text)
    text = text.lower().strip()
    text = _MULTI_SPACE.sub(" ", text)
    return text


def clean_arabic_text(text: str) -> str:
    """Light-touch cleaning for Wikipedia content before storing/displaying.

    Removes wiki-specific noise ([عدل], [1], [edit]) and normalizes
    whitespace. Does NOT change alef/ya variants so names stay intact.
    """
    text = unicodedata.normalize("NFC", text)
    text = _TASHKEEL.sub("", text)
    text = _TATWEEL.sub("", text)
    text = _WIKI_REFS.sub("", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()
