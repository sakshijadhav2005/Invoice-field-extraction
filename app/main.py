import logging
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.schema import ExtractionResponse, ConfidenceScores
from app.pdf_text import extract_pdf_document
from app.fields import extract_invoice_fields

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Bruviti Invoice Field Extractor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_HTML = BASE_DIR / "static" / "index.html"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit

@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
def chrome_devtools_endpoint():
    """Silently handle Chrome DevTools auto-probe without 404 logs."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index_page():
    if STATIC_HTML.exists():
        return HTMLResponse(content=STATIC_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Invoice Field Extractor</h1><p>Static UI not found.</p>")

@app.post("/extract", response_model=ExtractionResponse)
async def extract_invoice(file: UploadFile = File(...)):
    # 1. Validate file presence and filename
    if not file or not file.filename:
        logger.warning("Upload rejected: No file or filename provided.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")
    
    filename_lower = file.filename.lower()
    if not filename_lower.endswith(".pdf"):
        logger.warning("Upload rejected: '%s' is not a PDF file.", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format for '{file.filename}'. Only PDF files are supported."
        )

    # 2. Read bytes and check size
    content = await file.read()
    if len(content) == 0:
        logger.warning("Upload rejected: '%s' is an empty 0-byte file.", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded PDF file '{file.filename}' is empty (0 bytes)."
        )
    if len(content) > MAX_FILE_SIZE:
        logger.warning("Upload rejected: '%s' exceeds %d MB.", file.filename, MAX_FILE_SIZE // (1024 * 1024))
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB."
        )

    # 3. Basic PDF signature check
    if b"%PDF" not in content[:1024]:
        logger.warning("Upload rejected: '%s' lacks valid %%PDF header signature.", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{file.filename}' content does not have a valid PDF header."
        )

    # 4. Extract text layer and structured lines
    try:
        doc_info = extract_pdf_document(content)
    except Exception as e:
        # Corrupt or encrypted PDF -> return 200 all-null with warning
        return ExtractionResponse(
            vendor="unknown",
            confidence=ConfidenceScores(
                invoice_number=0.0, invoice_date=0.0, due_date=0.0,
                subtotal=0.0, tax=0.0, total=0.0, currency=0.0, vendor=0.0
            ),
            warnings=[f"Failed to parse PDF document (corrupt or encrypted): {str(e)}"]
        )

    # 5. Extract invoice fields
    try:
        return extract_invoice_fields(doc_info)
    except Exception as e:
        return ExtractionResponse(
            vendor="unknown",
            confidence=ConfidenceScores(
                invoice_number=0.0, invoice_date=0.0, due_date=0.0,
                subtotal=0.0, tax=0.0, total=0.0, currency=0.0, vendor=0.0
            ),
            warnings=[f"Extraction error encountered: {str(e)}"]
        )
