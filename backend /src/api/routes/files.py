from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from typing import List

from src.services import conversion_service as conv
from src.services.intent_parser import plan_conversion

router = APIRouter(prefix="/files")

MAX_FILES = 10


@router.post("/convert")
async def convert_files(
    command: str = Form(...),
    files: List[UploadFile] = File(...),
):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files allowed.")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    filenames = [f.filename for f in files]
    plan = plan_conversion(command, filenames)
    file_bytes = [await f.read() for f in files]
    extensions = plan["source_extensions"]
    target = plan["target_format"]
    operation = plan["operation"]

    try:
        # --- Image format conversion ---
        if target in ("jpg", "png", "webp") and all(ext in ("jpg", "jpeg", "png", "webp") for ext in extensions):
            fmt_map = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}
            if len(file_bytes) == 1:
                result = conv.convert_image_format(file_bytes[0], fmt_map[target])
                return Response(content=result, media_type=f"image/{target}")
            else:
                outputs = [
                    (f"converted_{i+1}.{target}", conv.convert_image_format(b, fmt_map[target]))
                    for i, b in enumerate(file_bytes)
                ]
                zipped = conv.zip_files(outputs)
                return Response(content=zipped, media_type="application/zip")

        # --- Images -> PDF (single or multiple) ---
        if target == "pdf" and all(ext in ("jpg", "jpeg", "png", "webp") for ext in extensions):
            result = conv.images_to_pdf(file_bytes)
            return Response(content=result, media_type="application/pdf")

        # --- Merge PDFs ---
        if operation == "merge" and all(ext == "pdf" for ext in extensions):
            result = conv.merge_pdfs(file_bytes)
            return Response(content=result, media_type="application/pdf")

        # --- Split PDF ---
        if operation == "split" and extensions == ["pdf"]:
            outputs = conv.split_pdf(file_bytes[0])
            zipped = conv.zip_files(outputs)
            return Response(content=zipped, media_type="application/zip")

        # --- PDF -> images ---
        if target in ("jpg", "png") and extensions == ["pdf"]:
            outputs = conv.pdf_to_images(file_bytes[0], image_format=target.upper())
            zipped = conv.zip_files(outputs)
            return Response(content=zipped, media_type="application/zip")

        # --- PDF -> text ---
        if target == "txt" and extensions == ["pdf"]:
            text = conv.pdf_to_text(file_bytes[0])
            return Response(content=text.encode("utf-8"), media_type="text/plain")

        # --- PDF -> docx (text-based) ---
        if target == "docx" and extensions == ["pdf"]:
            text = conv.pdf_to_text(file_bytes[0])
            result = conv.text_to_docx(text)
            return Response(
                content=result,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # --- TXT -> PDF ---
        if target == "pdf" and extensions == ["txt"]:
            text = file_bytes[0].decode("utf-8")
            result = conv.text_to_pdf(text)
            return Response(content=result, media_type="application/pdf")

        # --- TXT -> docx ---
        if target == "docx" and extensions == ["txt"]:
            text = file_bytes[0].decode("utf-8")
            result = conv.text_to_docx(text)
            return Response(
                content=result,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # --- DOCX -> txt ---
        if target == "txt" and extensions == ["docx"]:
            text = conv.docx_to_text(file_bytes[0])
            return Response(content=text.encode("utf-8"), media_type="text/plain")

        # --- DOCX -> PDF (text-based) ---
        if target == "pdf" and extensions == ["docx"]:
            result = conv.docx_to_pdf_via_text(file_bytes[0])
            return Response(content=result, media_type="application/pdf")

        # --- CSV -> XLSX ---
        if target == "xlsx" and extensions == ["csv"]:
            result = conv.csv_to_xlsx(file_bytes[0])
            return Response(
                content=result,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # --- XLSX -> CSV ---
        if target == "csv" and extensions == ["xlsx"]:
            result = conv.xlsx_to_csv(file_bytes[0])
            return Response(content=result, media_type="text/csv")

        # --- Rotate PDF ---
        if operation == "rotate" and extensions == ["pdf"]:
            result = conv.rotate_pdf(file_bytes[0], 90)
            return Response(content=result, media_type="application/pdf")

        # --- Rotate image ---
        if operation == "rotate" and extensions[0] in ("jpg", "jpeg", "png", "webp"):
            result = conv.rotate_image(file_bytes[0], 90)
            return Response(content=result, media_type=f"image/{extensions[0]}")

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not determine a supported conversion from that command "
                "and file type(s). Try being more specific, e.g. "
                "'convert this PDF to text' or 'merge these PDFs'."
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
