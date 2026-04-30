import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, Response
from ..models.schemas import FraudReport
from ..services.session_manager import session_manager
from ..services.pdf_extraction import extract_invoice_data
from ..services.report_generator import generate_pdf_report
from ..agents.fraud_agent import run_verification_pipeline
from ..services.coforge_llm import ainvoke_llm
from ..utils.guardrails import apply_guardrails
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "25")) * 1024 * 1024

@router.post("/session")
async def create_session():
    session = session_manager.create_session()
    return {
        "session_id": session.session_id,
        "message": "Upload an invoice PDF for fraud analysis",
        "chat_history": [m.model_dump() for m in session.chat_history]
    }

@router.post("/upload/{session_id}")
async def upload_document(session_id: str, file: UploadFile = File(...)):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size must be under {MAX_FILE_SIZE // (1024*1024)}MB")

    session.file_bytes = file_bytes
    session.file_name = file.filename
    session.status = "uploaded"
    size_kb = len(file_bytes) / 1024
    session_manager.add_message(session_id, "user", f"📎 Uploaded: {file.filename}")
    session_manager.add_message(session_id, "assistant", f"✅ Received **{file.filename}** ({size_kb:.1f} KB). Click Analyze to start fraud detection.")
    session_manager.update_session(session)
    return {"session_id": session_id, "file_name": file.filename, "message": f"File uploaded successfully. Size: {size_kb:.1f} KB", "status": "uploaded"}

@router.post("/extract/{session_id}")
async def extract_document(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.file_bytes:
        raise HTTPException(status_code=400, detail="No file uploaded")
    try:
        session.status = "extracting"
        invoice_data = extract_invoice_data(session.file_bytes, use_llm=True)
        invoice_data.raw_text = invoice_data.raw_text[:500]  # Trim for storage
        session.invoice_data = invoice_data
        session.status = "extracted"
        session_manager.add_message(session_id, "assistant", "✅ Data extraction complete! Running fraud verification...", message_type="extraction", data=invoice_data.model_dump())
        session_manager.update_session(session)
        return {"session_id": session_id, "invoice_data": invoice_data.model_dump(), "message": "Extraction complete", "llm_used": True}
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@router.post("/verify/{session_id}")
async def verify_document(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.invoice_data:
        raise HTTPException(status_code=400, detail="No extracted data — run extraction first")

    async def stream_pipeline():
        async for update in run_verification_pipeline(session.invoice_data, session_id, session.file_name):
            yield json.dumps(update) + "\n"
            if update.get("type") == "report":
                from ..models.schemas import FraudReport
                report = FraudReport(**update["report"])
                session.fraud_report = report
                session.status = "complete"
                session_manager.update_session(session)

    return StreamingResponse(stream_pipeline(), media_type="application/x-ndjson")

@router.get("/report/{session_id}")
async def get_report(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.fraud_report:
        raise HTTPException(status_code=400, detail="No report available yet")
    return session.fraud_report.model_dump()

@router.get("/report/{session_id}/pdf")
async def get_report_pdf(session_id: str):
    session = session_manager.get_session(session_id)
    if not session or not session.fraud_report:
        raise HTTPException(status_code=404, detail="Report not found")
    pdf_bytes = generate_pdf_report(session.fraud_report)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="fraud-report-{session_id[:8]}.pdf"'})

@router.get("/chat/{session_id}")
async def get_chat(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "chat_history": [m.model_dump() for m in session.chat_history]}

@router.post("/chat/{session_id}/message")
async def send_message(session_id: str, body: dict):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user_message = body.get("message", "")
    session_manager.add_message(session_id, "user", user_message)
    
    # Build context for LLM
    context = ""
    if session.fraud_report:
        context = f"Fraud report: Verdict={session.fraud_report.verdict.value}, Flags={session.fraud_report.total_flags}, Total=${session.invoice_data.total if session.invoice_data else 0:.2f}"
    
    try:
        prompt = f"""You are a fraud detection assistant for NexusIQ. {context}
        
User question: {user_message}

Answer helpfully and concisely based on the fraud analysis context."""
        response = await ainvoke_llm(prompt)
        response = apply_guardrails(response)
    except Exception:
        response = "I'm sorry, I couldn't process your question right now."
    
    session_manager.add_message(session_id, "assistant", response)
    return {"response": response}
