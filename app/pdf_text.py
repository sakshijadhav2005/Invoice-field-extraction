import fitz  # PyMuPDF
from typing import List, Optional
from pydantic import BaseModel

class WordBox(BaseModel):
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

class LineBox(BaseModel):
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    words: List[WordBox] = []

class PageInfo(BaseModel):
    page_num: int
    width: float
    height: float
    text: str
    lines: List[LineBox] = []

class DocumentInfo(BaseModel):
    has_text_layer: bool
    full_text: str
    pages: List[PageInfo] = []

def extract_pdf_document(pdf_bytes: bytes) -> DocumentInfo:
    """
    Parses a PDF from bytes using PyMuPDF (fitz).
    Extracts word bounding boxes, clusters words into lines by vertical alignment,
    and returns full text and structured spatial line models.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return DocumentInfo(has_text_layer=False, full_text="", pages=[])

    pages_info: List[PageInfo] = []
    full_text_chunks: List[str] = []

    for page_idx, page in enumerate(doc):
        page_text = page.get_text("text") or ""
        full_text_chunks.append(page_text)

        # Extract words: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        raw_words = page.get_text("words") or []
        word_boxes: List[WordBox] = [
            WordBox(
                text=w[4],
                x0=float(w[0]),
                y0=float(w[1]),
                x1=float(w[2]),
                y1=float(w[3])
            )
            for w in raw_words
        ]

        # Cluster words into lines based on y0 proximity (tolerance ~4 points)
        # Sort words primarily by y0, then x0
        word_boxes.sort(key=lambda w: (round(w.y0 / 4) * 4, w.x0))

        lines: List[LineBox] = []
        current_line_words: List[WordBox] = []
        current_y_baseline: Optional[float] = None

        for wb in word_boxes:
            if current_y_baseline is None:
                current_y_baseline = wb.y0
                current_line_words.append(wb)
            elif abs(wb.y0 - current_y_baseline) <= 4.0:
                current_line_words.append(wb)
            else:
                # Finish current line
                if current_line_words:
                    current_line_words.sort(key=lambda w: w.x0)
                    line_text = " ".join(w.text for w in current_line_words)
                    lx0 = min(w.x0 for w in current_line_words)
                    ly0 = min(w.y0 for w in current_line_words)
                    lx1 = max(w.x1 for w in current_line_words)
                    ly1 = max(w.y1 for w in current_line_words)
                    lines.append(LineBox(
                        text=line_text,
                        x0=lx0,
                        y0=ly0,
                        x1=lx1,
                        y1=ly1,
                        words=current_line_words
                    ))
                current_line_words = [wb]
                current_y_baseline = wb.y0

        if current_line_words:
            current_line_words.sort(key=lambda w: w.x0)
            line_text = " ".join(w.text for w in current_line_words)
            lx0 = min(w.x0 for w in current_line_words)
            ly0 = min(w.y0 for w in current_line_words)
            lx1 = max(w.x1 for w in current_line_words)
            ly1 = max(w.y1 for w in current_line_words)
            lines.append(LineBox(
                text=line_text,
                x0=lx0,
                y0=ly0,
                x1=lx1,
                y1=ly1,
                words=current_line_words
            ))

        # Sort lines strictly by y0 top-to-bottom
        lines.sort(key=lambda l: l.y0)

        pages_info.append(PageInfo(
            page_num=page_idx + 1,
            width=float(page.rect.width),
            height=float(page.rect.height),
            text=page_text,
            lines=lines
        ))

    combined_text = "\n\n".join(full_text_chunks).strip()
    has_text = len(combined_text) > 0 and any(len(p.lines) > 0 for p in pages_info)

    return DocumentInfo(
        has_text_layer=has_text,
        full_text=combined_text,
        pages=pages_info
    )
