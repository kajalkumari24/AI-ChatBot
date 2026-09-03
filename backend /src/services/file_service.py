from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import img2pdf
import pytesseract
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

try:
    import pandas as pd
except ImportError:  
    pd = None


MAX_FILES = 10
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  
OCR_MAX_DIMENSION = 2000  

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
PDF_EXTS = {".pdf"}
CSV_EXTS = {".csv"}
TXT_EXTS = {".txt"}
ALL_SUPPORTED_EXTS = IMAGE_EXTS | PDF_EXTS | CSV_EXTS | TXT_EXTS


class FileCategory(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    CSV = "csv"
    TXT = "txt"
    UNSUPPORTED = "unsupported"


class Intent(str, Enum):
    IMAGE_TO_PDF = "IMAGE_TO_PDF"
    MERGE_PDF = "MERGE_PDF"
    MIXED_PDF = "MIXED_PDF"
    CSV_ANALYSIS = "CSV_ANALYSIS"
    TEXT_ANALYSIS = "TEXT_ANALYSIS"
    IMAGE_CHAT = "IMAGE_CHAT"          
    PDF_READ = "PDF_READ"              
    GENERIC_FILE_CHAT = "GENERIC_FILE_CHAT"


@dataclass
class ProcessedFile:
    filename: str
    category: FileCategory
    content: bytes


def _get_ext(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _sniff_category(filename: str, content: bytes) -> FileCategory:
    
    ext = _get_ext(filename)

    if ext in IMAGE_EXTS:
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            return FileCategory.IMAGE
        except (UnidentifiedImageError, Exception):
            raise HTTPException(
                status_code=400,
                detail=f"The uploaded image appears to be corrupted: {filename}",
            )

    if ext in PDF_EXTS:
        try:
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail=f"The uploaded PDF is password-protected: {filename}",
                )
            _ = len(reader.pages)
            return FileCategory.PDF
        except PdfReadError:
            raise HTTPException(
                status_code=400,
                detail=f"The uploaded PDF appears to be corrupted: {filename}",
            )

    if ext in CSV_EXTS:
        try:
            text = content.decode("utf-8-sig")
            csv.Sniffer().sniff(text[:4096])
            return FileCategory.CSV
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"The uploaded CSV appears to be invalid: {filename}",
            )

    if ext in TXT_EXTS:
        try:
            content.decode("utf-8")
            return FileCategory.TXT
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail=f"The uploaded text file is not valid UTF-8 text: {filename}",
            )

    raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")


async def validate_and_read(files: list[UploadFile]) -> list[ProcessedFile]:
    """Validate count/size/type and read every file into memory once,
    preserving upload order. Raises HTTPException on any problem."""
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES} files are allowed per request.",
        )

    processed: list[ProcessedFile] = []
    for f in files:
        content = await f.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"Empty file: {f.filename}")
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too large (max {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB): {f.filename}",
            )
        category = _sniff_category(f.filename, content)
        processed.append(ProcessedFile(filename=f.filename, category=category, content=content))

    return processed


_PDF_CONVERT_WORDS = (
    "convert", "make pdf", "create pdf", "turn", "into pdf", "as pdf",
    "export", "one pdf", "single pdf",
)
_MERGE_WORDS = ("merge", "combine", "join")
_PDF_WORD = "pdf"


def detect_intent(message: str, files: list[ProcessedFile]) -> Intent:
    msg = (message or "").lower()
    categories = {f.category for f in files}
    mentions_pdf = _PDF_WORD in msg
    mentions_merge = any(w in msg for w in _MERGE_WORDS)
    mentions_convert = any(w in msg for w in _PDF_CONVERT_WORDS)

    only_images = categories == {FileCategory.IMAGE}
    only_pdfs = categories == {FileCategory.PDF}
    images_and_pdfs = categories == {FileCategory.IMAGE, FileCategory.PDF}

    if only_images and mentions_pdf and (mentions_convert or mentions_merge):
        return Intent.IMAGE_TO_PDF

    if only_pdfs:
        if len(files) > 1 and (mentions_merge or mentions_pdf):
            return Intent.MERGE_PDF
        return Intent.PDF_READ

    if images_and_pdfs and (mentions_pdf or mentions_merge or mentions_convert):
        return Intent.MIXED_PDF

    if categories == {FileCategory.CSV}:
        return Intent.CSV_ANALYSIS

    if categories == {FileCategory.TXT}:
        return Intent.TEXT_ANALYSIS

    if only_images:
        return Intent.IMAGE_CHAT

    return Intent.GENERIC_FILE_CHAT


def convert_images_to_pdf(files: list[ProcessedFile]) -> bytes:
  
    image_bytes_list = [f.content for f in files if f.category == FileCategory.IMAGE]
    if not image_bytes_list:
        raise HTTPException(status_code=400, detail="No valid images provided for PDF conversion.")
    try:
        return img2pdf.convert(image_bytes_list)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to convert images to PDF: {e}")


def merge_pdfs(files: list[ProcessedFile]) -> bytes:
    writer = PdfWriter()
    for f in files:
        if f.category != FileCategory.PDF:
            continue
        try:
            reader = PdfReader(io.BytesIO(f.content))
            for page in reader.pages:
                writer.add_page(page)
        except PdfReadError:
            raise HTTPException(status_code=400, detail=f"The uploaded PDF appears to be corrupted: {f.filename}")

    if len(writer.pages) == 0:
        raise HTTPException(status_code=400, detail="No valid PDF pages found to merge.")

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def combine_mixed_to_pdf(files: list[ProcessedFile]) -> bytes:
    
    writer = PdfWriter()

    for f in files:
        if f.category == FileCategory.IMAGE:
            try:
                page_pdf_bytes = img2pdf.convert([f.content])
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process image '{f.filename}': {e}")
            reader = PdfReader(io.BytesIO(page_pdf_bytes))
        elif f.category == FileCategory.PDF:
            try:
                reader = PdfReader(io.BytesIO(f.content))
            except PdfReadError:
                raise HTTPException(status_code=400, detail=f"The uploaded PDF appears to be corrupted: {f.filename}")
        else:
            continue

        for page in reader.pages:
            writer.add_page(page)

    if len(writer.pages) == 0:
        raise HTTPException(status_code=400, detail="No valid pages found to combine.")

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def extract_pdf_text(file: ProcessedFile, max_chars: int = 8000) -> str:
    """Best-effort text extraction from a single PDF, for use as LLM context
    when the user isn't asking for a merge/convert operation."""
    try:
        reader = PdfReader(io.BytesIO(file.content))
        parts = []
        for i, page in enumerate(reader.pages):
            parts.append(f"--- Page {i + 1} ---\n{page.extract_text() or ''}")
        text = "\n".join(parts).strip()
    except Exception:
        text = ""

    if not text:
        return f"[No extractable text found in {file.filename} — it may be a scanned/image-only PDF.]"

    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return text

def read_csv_bytes(file: ProcessedFile, max_preview_rows: int = 20) -> str:
    if pd is None:
        raise HTTPException(
            status_code=500,
            detail="pandas is not installed on the server; CSV analysis is unavailable.",
        )
    try:
        df = pd.read_csv(io.BytesIO(file.content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV '{file.filename}': {e}")

    n_rows, n_cols = df.shape
    dtypes = ", ".join(f"{c} ({t})" for c, t in df.dtypes.astype(str).items())
    preview = df.head(max_preview_rows).to_csv(index=False)

    summary_parts = [
        f"CSV file: {file.filename}",
        f"Rows: {n_rows}, Columns: {n_cols}",
        f"Columns and types: {dtypes}",
    ]

    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        stats = numeric_df.describe().to_csv()
        summary_parts.append(f"Numeric column statistics:\n{stats}")

    summary_parts.append(f"Preview (first {min(max_preview_rows, n_rows)} rows):\n{preview}")

    return "\n\n".join(summary_parts)


def read_text_bytes(file: ProcessedFile, max_chars: int = 12000) -> str:
    text = file.content.decode("utf-8")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return f"Text file: {file.filename}\n\n{text}"


def _downscale_for_ocr(img: Image.Image) -> Image.Image:
    img = img.copy()
    img.thumbnail((OCR_MAX_DIMENSION, OCR_MAX_DIMENSION))
    return img


def ocr_images(files: list[ProcessedFile]) -> str:
    """Run OCR over each image in upload order and return combined text
    with clear per-image separators, per project spec section 18."""
    blocks = []
    for i, f in enumerate(files):
        if f.category != FileCategory.IMAGE:
            continue
        try:
            img = Image.open(io.BytesIO(f.content))
            img = _downscale_for_ocr(img)
            text = pytesseract.image_to_string(img).strip() or "[No text detected]"
        except Exception as e:
            text = f"[OCR failed for this image: {e}]"
        blocks.append(f"--- Image {i + 1} ({f.filename}) ---\n{text}")

    return "\n\n".join(blocks)


def first_image_as_pil(files: list[ProcessedFile]) -> Optional[Image.Image]:
    """Used for the single-image chat path, which is passed directly to the
    vision-capable LLM instead of going through OCR (better quality)."""
    for f in files:
        if f.category == FileCategory.IMAGE:
            return Image.open(io.BytesIO(f.content))
    return None