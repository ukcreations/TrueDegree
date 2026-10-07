"""
routers/ocr_router.py — OCR extraction and document analysis endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.ocr_service import extract_text_and_meta
from services.analyzer_service import analyze_uploaded_document

router = APIRouter()


class OCRResponse(BaseModel):
    raw_text:            str
    roll_number:         Optional[str] = None
    confidence:          str           # "high" | "medium" | "low"
    student_name:        Optional[str] = None
    university_name:     Optional[str] = None
    degree:              Optional[str] = None
    is_academic:         bool          = True
    category:            str           = "Academic Document"
    verdict:             str           = "ANALYZED"
    authenticity_score:  int           = 0
    message:             str           = ""
    audit_checks:        List[Dict[str, Any]] = []
    risk_flags:          List[str]     = []


@router.post("/ocr", response_model=OCRResponse, summary="Extract text and entities from certificate via OCR")
async def ocr_certificate(file: UploadFile = File(...)):
    """
    Upload a PDF or image file.
    Extracts text and performs automatic classification & entity extraction.
    """
    allowed = {
        "application/pdf", "image/png", "image/jpeg", "image/jpg",
        "image/tiff", "image/bmp", "image/webp"
    }
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file_bytes = await file.read()

    try:
        raw_text, metadata = await extract_text_and_meta(file_bytes, file.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

    analysis = analyze_uploaded_document(file_bytes, raw_text, metadata)
    entities = analysis.get("extracted_entities", {})

    return OCRResponse(
        raw_text=raw_text[:5000],
        roll_number=entities.get("roll_number"),
        confidence=entities.get("roll_confidence", "medium"),
        student_name=entities.get("student_name"),
        university_name=entities.get("university_name"),
        degree=entities.get("degree"),
        is_academic=analysis.get("is_academic", True),
        category=analysis.get("category", "Unknown"),
        verdict=analysis.get("verdict", "ANALYZED"),
        authenticity_score=analysis.get("authenticity_score", 0),
        message=analysis.get("message", ""),
        audit_checks=analysis.get("audit_checks", []),
        risk_flags=analysis.get("risk_flags", []),
    )


@router.post("/analyze", summary="Perform deep authenticity & relevance audit on any uploaded document")
async def analyze_document(file: UploadFile = File(...)):
    """
    Comprehensive document audit:
    - Verifies whether the document is an academic degree/marksheet vs unrelated document
    - Performs forensic verification of authenticity (Real vs Fake vs Tampered)
    """
    file_bytes = await file.read()
    raw_text, metadata = await extract_text_and_meta(file_bytes, file.content_type or "application/pdf")
    analysis = analyze_uploaded_document(file_bytes, raw_text, metadata)
    return analysis
