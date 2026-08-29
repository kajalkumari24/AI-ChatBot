"""
api/routes/convert.py — POST /api/convert-to-pdf
Simple file conversion, no LLM involved.
"""
import img2pdf
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response

router = APIRouter()


@router.post("/convert-to-pdf")
async def convert_to_pdf(file: UploadFile = File(...)):
    image_bytes = await file.read()
    pdf_bytes = img2pdf.convert(image_bytes)
    return Response(content=pdf_bytes, media_type="application/pdf")
