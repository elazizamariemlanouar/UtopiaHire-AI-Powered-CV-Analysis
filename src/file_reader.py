import pdfplumber
from docx import Document

def extract_text_from_pdf(file_path):
    """Extract text from PDF file using pdfplumber."""
    text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text.append(t)
    return "\n".join(text).strip()

def extract_text_from_docx(file_path):
    """Extract text from DOCX file."""
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs).strip()

def extract_resume_text(file_path):
    """Detect file type and extract text."""
    lower = file_path.lower()

    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif lower.endswith(".docx"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type. Only PDF and DOCX are allowed.")
