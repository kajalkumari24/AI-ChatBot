import base64
from typing import List, Optional

from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session

from src.core.rag_engine import ask
from src.services import memory, history_service, file_service
from src.services.file_service import Intent, FileCategory
from src.db.database import get_db

router = APIRouter()


@router.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: str = Form("default_session"),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Filter out the empty placeholder FastAPI can send when no files are chosen.
    uploaded = [f for f in files if f and f.filename] if files else []

    history_service.get_or_create_conversation(db, session_id)

    if not uploaded:
        # ---- Existing text-only flow, unchanged ----
        reply = ask(session_id=session_id, user_message=message, image=None)
        history_service.add_message(db, session_id, "user", message)
        history_service.add_message(db, session_id, "assistant", reply)
        return {"reply": reply, "session_id": session_id, "action": "chat"}

    processed = await file_service.validate_and_read(uploaded)
    intent = file_service.detect_intent(message, processed)
    filenames = [f.filename for f in processed]

    # ---- Pure file-conversion intents: no LLM call, return a downloadable PDF ----
    if intent in (Intent.IMAGE_TO_PDF, Intent.MERGE_PDF, Intent.MIXED_PDF):
        if intent == Intent.IMAGE_TO_PDF:
            pdf_bytes = file_service.convert_images_to_pdf(processed)
            reply = f"Converted {len(processed)} image(s) to PDF."
        elif intent == Intent.MERGE_PDF:
            pdf_bytes = file_service.merge_pdfs(processed)
            reply = f"Merged {len(processed)} PDF(s) into one file."
        else:
            pdf_bytes = file_service.combine_mixed_to_pdf(processed)
            reply = f"Combined {len(processed)} file(s) into one PDF."

        display_user_msg = f"[Files: {', '.join(filenames)}] {message}"
        history_service.add_message(db, session_id, "user", display_user_msg)
        history_service.add_message(db, session_id, "assistant", reply)

        return {
            "reply": reply,
            "session_id": session_id,
            "action": "download_pdf",
            "filename": "converted.pdf",
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        }

    # ---- Single image, no conversion requested: existing vision-LLM path ----
    if intent == Intent.IMAGE_CHAT and len(processed) == 1:
        image_obj = file_service.first_image_as_pil(processed)
        reply = ask(session_id=session_id, user_message=message, image=image_obj)
        history_service.add_message(db, session_id, "user", f"[Image Uploaded] {message}")
        history_service.add_message(db, session_id, "assistant", reply)
        return {"reply": reply, "session_id": session_id, "action": "chat"}

    # ---- Multiple images, no conversion requested: OCR all, feed as context ----
    if intent == Intent.IMAGE_CHAT:
        extra_context = (
            "The user attached multiple images. Extracted text (OCR), in upload order:\n\n"
            + file_service.ocr_images(processed)
        )
        display_user_msg = f"[Files: {', '.join(filenames)}] {message}"
        reply = ask(session_id=session_id, user_message=display_user_msg, extra_context=extra_context)
        history_service.add_message(db, session_id, "user", display_user_msg)
        history_service.add_message(db, session_id, "assistant", reply)
        return {"reply": reply, "session_id": session_id, "action": "chat"}

    # ---- CSV / TXT / single-PDF-read / generic: extract text, feed as context ----
    extra_context_parts = []
    for f in processed:
        if f.category == FileCategory.CSV:
            extra_context_parts.append(file_service.read_csv_bytes(f))
        elif f.category == FileCategory.TXT:
            extra_context_parts.append(file_service.read_text_bytes(f))
        elif f.category == FileCategory.PDF:
            extra_context_parts.append(file_service.extract_pdf_text(f))

    extra_context = (
        "The user attached the following file(s):\n\n" + "\n\n---\n\n".join(extra_context_parts)
        if extra_context_parts
        else None
    )

    display_user_msg = f"[Files: {', '.join(filenames)}] {message}"
    reply = ask(session_id=session_id, user_message=display_user_msg, extra_context=extra_context)
    history_service.add_message(db, session_id, "user", display_user_msg)
    history_service.add_message(db, session_id, "assistant", reply)

    return {"reply": reply, "session_id": session_id, "action": "chat"}


@router.post("/clear")
async def clear_chat_history(session_id: str = Form("default_session"), db: Session = Depends(get_db)):
    memory.clear_session(session_id)
    history_service.clear_messages(db, session_id)
    return {"status": "success", "message": "Memory cleared"}


@router.get("/health")
def health():
    return {"status": "ok"}