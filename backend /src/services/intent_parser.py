"""
services/intent_parser.py — detects which conversion the user wants from
a natural-language message plus the file extensions they uploaded.
Keyword-based (not LLM-based) so it's fast, free, and predictable.
"""
import re

TARGET_FORMAT_WORDS = {
    "pdf": "pdf",
    "jpg": "jpg", "jpeg": "jpg",
    "png": "png",
    "webp": "webp",
    "docx": "docx", "word": "docx",
    "txt": "txt", "text": "txt",
    "csv": "csv",
    "xlsx": "xlsx", "excel": "xlsx",
}

VERB_WORDS = {
    "merge": "merge",
    "combine": "merge",
    "split": "split",
    "separate": "split",
    "rotate": "rotate",
    "compress": "compress",
    "resize": "resize",
    "crop": "crop",
    "convert": "convert",
}


def detect_target_format(message: str) -> str | None:
    """
    Prefers the format mentioned after "to"/"into" (the actual target),
    e.g. "PDF to Word" -> docx, not pdf. Falls back to the first format
    word found anywhere if no "to X" pattern matches.
    """
    message_lower = message.lower()

    to_match = re.search(r"\b(?:to|into)\s+(?:one\s+|a\s+)?(\w+)", message_lower)
    if to_match:
        candidate = to_match.group(1)
        if candidate in TARGET_FORMAT_WORDS:
            return TARGET_FORMAT_WORDS[candidate]

    for word, fmt in TARGET_FORMAT_WORDS.items():
        if re.search(rf"\b{word}\b", message_lower):
            return fmt
    return None


def detect_verb(message: str) -> str:
    message_lower = message.lower()
    for word, verb in VERB_WORDS.items():
        if re.search(rf"\b{word}\b", message_lower):
            return verb
    return "convert"


def get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def plan_conversion(message: str, filenames: list[str]) -> dict:
    """
    Returns a plan dict describing what operation to run:
    {"operation": str, "target_format": str | None, "source_extensions": [...]}
    The API route uses this to decide which conversion_service function to call.
    """
    verb = detect_verb(message)
    target = detect_target_format(message)
    extensions = [get_extension(f) for f in filenames]

    return {
        "operation": verb,
        "target_format": target,
        "source_extensions": extensions,
        "file_count": len(filenames),
    }
