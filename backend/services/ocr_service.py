"""
services/ocr_service.py — Multi-engine OCR & Text Extraction Service
Supports direct digital PDF extraction (PyMuPDF), table extraction (pdfplumber),
scanned document OCR (RapidOCR on ONNX runtime), and image files.
"""
import io
import re
import asyncio
from typing import Optional, Tuple, Dict, Any, List

import numpy as np
from PIL import Image

# Import PyMuPDF (fitz)
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# Import pdfplumber
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# Import RapidOCR
try:
    from rapidocr_onnxruntime import RapidOCR
    _rapid_ocr = RapidOCR()
    HAS_RAPID_OCR = True
except Exception:
    _rapid_ocr = None
    HAS_RAPID_OCR = False

# Optional Tesseract fallback
try:
    import pytesseract
    from config import get_settings
    settings = get_settings()
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    HAS_TESSERACT = True
except Exception:
    HAS_TESSERACT = False


def _ocr_image_np(img_np: np.ndarray) -> str:
    """Run OCR on a numpy image array using RapidOCR or fallback to Tesseract."""
    if HAS_RAPID_OCR and _rapid_ocr is not None:
        try:
            result, _ = _rapid_ocr(img_np)
            if result:
                return "\n".join([line[1] for line in result if line and len(line) > 1])
        except Exception:
            pass

    if HAS_TESSERACT:
        try:
            pil_img = Image.fromarray(img_np)
            return pytesseract.image_to_string(pil_img, config=r"--oem 3 --psm 6")
        except Exception:
            pass

    return ""


def _extract_from_pdf(pdf_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Extract text and metadata from PDF bytes.
    Uses PyMuPDF (fitz) for fast text extraction. If page text is sparse/scanned,
    renders page to image and runs RapidOCR.
    """
    extracted_text_blocks = []
    metadata = {
        "page_count": 0,
        "format": "PDF",
        "has_digital_text": False,
        "producer": "",
        "creator": "",
        "title": "",
        "is_scanned": False,
    }

    if not HAS_FITZ:
        return "", metadata

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        metadata["page_count"] = len(doc)
        doc_meta = doc.metadata or {}
        metadata["producer"] = doc_meta.get("producer", "")
        metadata["creator"] = doc_meta.get("creator", "")
        metadata["title"] = doc_meta.get("title", "")

        total_digital_chars = 0

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text("text").strip()
            total_digital_chars += len(page_text)

            if len(page_text) >= 40:
                extracted_text_blocks.append(page_text)
            else:
                # Page seems to be a scanned image or sparse text, render & OCR
                metadata["is_scanned"] = True
                try:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                    img_np = np.array(img)
                    ocr_res = _ocr_image_np(img_np)
                    if ocr_res:
                        extracted_text_blocks.append(ocr_res)
                    elif page_text:
                        extracted_text_blocks.append(page_text)
                except Exception:
                    if page_text:
                        extracted_text_blocks.append(page_text)

        metadata["has_digital_text"] = total_digital_chars > 80
        doc.close()

    except Exception as e:
        # Fallback to pdfplumber if fitz fails
        if HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for p in pdf.pages:
                        t = p.extract_text()
                        if t:
                            extracted_text_blocks.append(t)
            except Exception:
                pass

    full_text = "\n".join(extracted_text_blocks).strip()
    return full_text, metadata


def _extract_from_image(image_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text from standard image bytes (PNG, JPG, TIFF, etc.)."""
    metadata = {
        "page_count": 1,
        "format": "IMAGE",
        "has_digital_text": False,
        "is_scanned": True,
    }

    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        metadata["width"] = pil_img.width
        metadata["height"] = pil_img.height
        img_np = np.array(pil_img)
        text = _ocr_image_np(img_np)
        return text.strip(), metadata
    except Exception as e:
        return "", metadata


async def extract_text_from_bytes(file_bytes: bytes, content_type: str) -> str:
    """Async wrapper that returns text string from file bytes."""
    text, _ = await extract_text_and_meta(file_bytes, content_type)
    return text


async def extract_text_and_meta(file_bytes: bytes, content_type: str) -> Tuple[str, Dict[str, Any]]:
    """Async wrapper that runs text extraction and metadata inspection in executor thread."""
    loop = asyncio.get_event_loop()

    if content_type == "application/pdf":
        return await loop.run_in_executor(None, _extract_from_pdf, file_bytes)
    else:
        return await loop.run_in_executor(None, _extract_from_image, file_bytes)


# ─── Entity Extraction Functions ──────────────────────────────────────────────

def parse_roll_number(text: str) -> Tuple[Optional[str], str]:
    """
    Extract Roll Number / Registration Number / Enrollment / PRN from text.
    Returns (roll_number, confidence).
    """
    patterns = [
        # Explicit labels (High confidence)
        (r"(?:Roll\s*(?:No|Number|No\.)\s*[:\-\#]?\s*)([A-Z0-9\-\/]{4,25})", "high"),
        (r"(?:Registration\s*(?:No|Number|No\.)\s*[:\-\#]?\s*)([A-Z0-9\-\/]{4,25})", "high"),
        (r"(?:Regd\.?\s*(?:No|Number)\s*[:\-\#]?\s*)([A-Z0-9\-\/]{4,25})", "high"),
        (r"(?:Enrol(?:l?ment)?\s*(?:No|Number|No\.)\s*[:\-\#]?\s*)([A-Z0-9\-\/]{4,25})", "high"),
        (r"(?:PRN\s*(?:No|Number)?\s*[:\-\#]?\s*)([A-Z0-9]{6,22})", "high"),
        (r"(?:Hall\s*Ticket\s*(?:No|Number)\s*[:\-\#]?\s*)([A-Z0-9]{6,22})", "high"),
        (r"(?:Seat\s*(?:No|Number)\s*[:\-\#]?\s*)([A-Z0-9]{4,20})", "high"),
        (r"(?:Certificate\s*(?:ID|No|Number)\s*[:\-\#]?\s*)([A-Z0-9\-]{4,25})", "high"),
        (r"(?:Student\s*ID\s*[:\-\#]?\s*)([A-Z0-9\-]{4,25})", "high"),

        # Medium confidence — structured academic IDs (e.g. 2411200010023, BTH20200123)
        (r"\b([0-9]{10,16})\b", "medium"),
        (r"\b([A-Z]{2,5}[0-9]{6,12})\b", "medium"),
        (r"\b([0-9]{2}[A-Z]{2,5}[0-9]{4,10})\b", "medium"),
    ]

    for pattern, conf in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip().upper()
            # Filter out non-roll tokens like dates or generic codes
            if not re.match(r"^(19|20)\d{2}[-/]\d{2}[-/]\d{2}$", candidate) and len(candidate) >= 4:
                return candidate, conf

    return None, "low"


def parse_student_name(text: str) -> Optional[str]:
    """Extract candidate / student name from text."""
    patterns = [
        r"(?:Student\s*Name|Candidate'?s?\s*Name|Name\s*of\s*(?:the\s*)?(?:Candidate|Student))\s*[:\-]?\s*([A-Z][A-Za-z\s.]{2,40})",
        r"(?:This\s+is\s+to\s+certify\s+that\s+)(?:Mr\.?|Ms\.?|Mrs\.?|Shri|Smt\.?)?\s*([A-Z][A-Za-z\s.]{2,40})",
        r"(?:conferred\s+upon\s+)(?:Mr\.?|Ms\.?|Mrs\.?|Shri|Smt\.?)?\s*([A-Z][A-Za-z\s.]{2,40})",
        r"(?:admitted\s+to\s+the\s+degree\s+of\s+[^,\n]+,\s*)(?:Mr\.?|Ms\.?|Mrs\.?|Shri|Smt\.?)?\s*([A-Z][A-Za-z\s.]{2,40})",
        r"(?:Name\s*[:\-]\s*)([A-Z][A-Za-z\s.]{2,40})",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Clean trailing whitespace/newlines or punctuation
            name = re.split(r"[\n,\r]", name)[0].strip()
            # Validate name length and structure (not a sentence)
            words = name.split()
            if 1 <= len(words) <= 5 and all(w.isalpha() or "." in w for w in words):
                # Filter out obvious false positives like "THIS IS", "BACHELOR OF"
                if not any(w.lower() in ("bachelor", "master", "doctor", "technology", "university", "examination") for w in words):
                    return name.upper()

    return None


def parse_university_name(text: str) -> Optional[str]:
    """Extract University, Institute, College, or Board name."""
    patterns = [
        # Prominent university phrases
        r"([A-Z][A-Za-z\s&,.]{3,70}(?:UNIVERSITY|INSTITUTE OF TECHNOLOGY|COLLEGE OF ENGINEERING|DEEMED UNIVERSITY|VIDYAPEETH|ACADEMY OF HIGHER EDUCATION))",
        r"(UNIVERSITY\s+OF\s+[A-Za-z\s]{3,40})",
        r"(CENTRAL\s+BOARD\s+OF\s+SECONDARY\s+EDUCATION|COUNCIL\s+FOR\s+THE\s+INDIAN\s+SCHOOL\s+CERTIFICATE\s+EXAMINATIONS|STATE\s+BOARD\s+OF\s+TECHNICAL\s+EDUCATION)",
        r"(INDIAN\s+INSTITUTE\s+OF\s+TECHNOLOGY[A-Za-z\s,]*)",
        r"(NATIONAL\s+INSTITUTE\s+OF\s+TECHNOLOGY[A-Za-z\s,]*)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            uni = m.group(1).strip()
            uni = re.split(r"[\n\r]", uni)[0].strip()
            # Remove leading/trailing non-alpha
            uni = re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", uni)
            if len(uni) >= 8:
                return uni.upper()

    return None


def parse_degree_name(text: str) -> Optional[str]:
    """Extract degree, diploma, or academic program title."""
    degrees = [
        r"(?:BACHELOR\s+OF\s+(?:TECHNOLOGY|ENGINEERING|SCIENCE|COMMERCE|ARTS|BUSINESS\s+ADMINISTRATION|COMPUTER\s+APPLICATIONS|PHARMACY|LAWS|EDUCATION|DENTAL\s+SURGERY|MEDICINE|ARCHITECTURE)[A-Za-z\s&(),-]*)",
        r"(?:MASTER\s+OF\s+(?:TECHNOLOGY|ENGINEERING|SCIENCE|COMMERCE|ARTS|BUSINESS\s+ADMINISTRATION|COMPUTER\s+APPLICATIONS|PHARMACY|LAWS|EDUCATION)[A-Za-z\s&(),-]*)",
        r"(?:DOCTOR\s+OF\s+PHILOSOPHY[A-Za-z\s&(),-]*)",
        r"\b(B\.?\s?TECH|B\.?\s?E|M\.?\s?TECH|M\.?\s?E|B\.?\s?SC|M\.?\s?SC|B\.?\s?CA|M\.?\s?CA|M\.?\s?BA|B\.?\s?BA|B\.?\s?COM|M\.?\s?COM|B\.?\s?A|M\.?\s?A|PH\.?D|MBBS|BDS|B\.?\s?PHARM)\b",
        r"(?:DIPLOMA\s+IN\s+[A-Za-z\s&(),-]{3,40})",
        r"(?:HIGHER\s+SECONDARY\s+(?:SCHOOL\s+)?CERTIFICATE|SENIOR\s+SCHOOL\s+CERTIFICATE)",
    ]

    for deg in degrees:
        m = re.search(deg, text, re.IGNORECASE)
        if m:
            clean = m.group(0).strip()
            clean = re.split(r"[\n\r]", clean)[0].strip()
            return clean.upper()

    return None


def parse_cgpa_or_marks(text: str) -> Dict[str, Any]:
    """Extract CGPA, SGPA, Percentage, Division, and Total Marks."""
    res: Dict[str, Any] = {}

    # CGPA / SGPA
    cgpa_m = re.search(r"\b(?:CGPA|GPA|SGPA|OGPA)\s*[:\-\=]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:\/\s*([0-9]+(?:\.[0-9]+)?))?", text, re.IGNORECASE)
    if cgpa_m:
        val = float(cgpa_m.group(1))
        scale = float(cgpa_m.group(2)) if cgpa_m.group(2) else (10.0 if val <= 10.0 else 100.0)
        res["cgpa"] = val
        res["cgpa_scale"] = scale

    # Percentage
    pct_m = re.search(r"\b(?:Percentage|Aggregate|Percent|Pct\.?)\s*[:\-\=]?\s*([0-9]+(?:\.[0-9]+)?)\s*\%?", text, re.IGNORECASE)
    if pct_m:
        res["percentage"] = float(pct_m.group(1))

    # Total Marks out of Maximum Marks
    total_m = re.search(r"\b(?:Total\s*Marks|Grand\s*Total|Aggregate\s*Marks)\s*[:\-\=]?\s*([0-9]+)\s*(?:\/|\s*out\s*of\s*)\s*([0-9]+)", text, re.IGNORECASE)
    if total_m:
        res["marks_obtained"] = int(total_m.group(1))
        res["max_marks"] = int(total_m.group(2))

    # Division / Class
    div_m = re.search(r"\b(?:Division|Class|Grade)\s*[:\-\=]?\s*([A-Za-z\s]{3,30})", text, re.IGNORECASE)
    if div_m:
        d = div_m.group(1).strip()
        d = re.split(r"[\n\r,]", d)[0].strip()
        if any(w.lower() in ("first", "second", "third", "distinction", "honours", "pass", "exemplary") for w in d.split()):
            res["division"] = d.title()

    return res


def extract_all_entities(text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Combine all extraction logic into a single cohesive entity report."""
    roll, roll_conf = parse_roll_number(text)
    student_name = parse_student_name(text)
    uni_name = parse_university_name(text)
    degree = parse_degree_name(text)
    grade_data = parse_cgpa_or_marks(text)

    # Date extraction
    date_m = re.search(r"\b(?:Date\s*(?:of\s*Issue)?|Issued\s*on|Dated)\s*[:\-]?\s*([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4}|[A-Za-z]+\s+[0-9]{1,2},\s*[0-9]{4}|[0-9]{4})", text, re.IGNORECASE)
    issue_date = date_m.group(1).strip() if date_m else None

    # Year of passing / Graduation year
    year_m = re.search(r"\b(?:Year\s*of\s*Passing|Year\s*of\s*Graduation|Graduated\s*in|Session|Batch)\s*[:\-]?\s*([0-9]{4}(?:-[0-9]{2,4})?)", text, re.IGNORECASE)
    passing_year = year_m.group(1).strip() if year_m else None

    return {
        "roll_number": roll,
        "roll_confidence": roll_conf,
        "student_name": student_name,
        "university_name": uni_name,
        "degree": degree,
        "grade_data": grade_data,
        "issue_date": issue_date,
        "passing_year": passing_year,
        "metadata": metadata or {},
    }
