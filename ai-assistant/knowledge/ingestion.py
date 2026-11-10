"""Document ingestion for RAG: PDF, DOCX, XLSX, PPTX, TXT, Markdown.

OCR for scanned documents is optional. Set `ocr_enabled=True` and install
pytesseract + tesseract-ocr to enable scanned PDF/image support.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md"}


@dataclass
class DocumentChunk:
    """A single chunk of a document ready for vector storage."""
    id: str
    content: str
    filename: str
    language: str
    project_id: Optional[str]
    metadata: Dict[str, Any]
    vector: Optional[List[float]] = None


@dataclass
class IngestionResult:
    """Result of ingesting a file, including change-detection info."""
    chunks: List[DocumentChunk]
    content_hash: str
    is_new: bool
    is_updated: bool
    old_content_hash: Optional[str] = None


class DocumentIngestor:
    """Parses supported file types into chunks for RAG ingestion.

    Change detection: call `has_changed(content_hash, stored_hash)` before
    ingesting to decide whether to create, update, or skip a document.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        ocr_enabled: bool = False,
        ocr_languages: Optional[List[str]] = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.ocr_enabled = ocr_enabled
        self.ocr_languages = ocr_languages or ["ara", "eng"]

    def is_supported(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS

    def has_changed(
        self,
        content_hash: str,
        stored_hash: Optional[str],
    ) -> Tuple[bool, Optional[str]]:
        """Compare content hash with stored hash.

        Returns (changed, old_hash). If stored_hash is None, the document is new.
        """
        if stored_hash is None:
            return True, None
        return content_hash != stored_hash, stored_hash

    def ingest_file(
        self,
        file_path: str,
        project_id: Optional[str] = None,
        language: str = "ar",
        stored_content_hash: Optional[str] = None,
    ) -> IngestionResult:
        """Read a file and return chunks with change-detection info."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        content_hash = self._hash_file(file_path)
        changed, old_hash = self.has_changed(content_hash, stored_content_hash)

        if ext == ".pdf":
            text, page_map = self._extract_pdf(path)
        elif ext == ".docx":
            text, page_map = self._extract_docx(path), {}
        elif ext == ".xlsx":
            text, page_map = self._extract_xlsx(path), {}
        elif ext == ".pptx":
            text, page_map = self._extract_pptx(path), {}
        else:
            text = path.read_text(encoding="utf-8")
            page_map = {}

        chunks = self._chunk_text(
            text=text,
            filename=path.name,
            content_hash=content_hash,
            project_id=project_id,
            language=language,
            page_map=page_map,
        )

        return IngestionResult(
            chunks=chunks,
            content_hash=content_hash,
            is_new=old_hash is None,
            is_updated=changed and old_hash is not None,
            old_content_hash=old_hash,
        )

    def ingest_text(
        self,
        text: str,
        filename: str,
        project_id: Optional[str] = None,
        language: str = "ar",
        stored_content_hash: Optional[str] = None,
    ) -> IngestionResult:
        """Ingest raw text directly with change detection."""
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        changed, old_hash = self.has_changed(content_hash, stored_content_hash)

        chunks = self._chunk_text(
            text=text,
            filename=filename,
            content_hash=content_hash,
            project_id=project_id,
            language=language,
        )

        return IngestionResult(
            chunks=chunks,
            content_hash=content_hash,
            is_new=old_hash is None,
            is_updated=changed and old_hash is not None,
            old_content_hash=old_hash,
        )

    # ------------------------------------------------------------------
    # File type extractors
    # ------------------------------------------------------------------
    def _extract_pdf(self, path: Path) -> Tuple[str, Dict[int, str]]:
        """Extract text from PDF. Returns (full_text, page_map).

        If OCR is enabled and a page has no extractable text, attempts OCR
        (requires pytesseract + tesseract-ocr installed).
        """
        try:
            import pypdf  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pypdf is required for PDF extraction") from exc

        reader = pypdf.PdfReader(str(path))
        parts: List[str] = []
        page_map: Dict[int, str] = {}

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            # OCR fallback for scanned pages
            if not page_text.strip() and self.ocr_enabled:
                try:
                    page_text = self._ocr_page(path, page_num - 1)
                except Exception as exc:
                    logger.warning("OCR failed for page %d: %s", page_num, exc)

            if page_text.strip():
                parts.append(f"[Page {page_num}] {page_text}")
                page_map[page_num] = page_text

        return "\n".join(parts), page_map

    def _ocr_page(self, path: Path, page_index: int) -> str:
        """OCR a single PDF page (optional, requires tesseract)."""
        try:
            import pytesseract  # type: ignore
            from pdf2image import convert_from_path  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "OCR requires pytesseract and pdf2image: pip install pytesseract pdf2image"
            ) from exc

        images = convert_from_path(
            str(path),
            first_page=page_index + 1,
            last_page=page_index + 1,
        )
        if not images:
            return ""
        lang = "+".join(self.ocr_languages)
        return pytesseract.image_to_string(images[0], lang=lang)

    def _extract_docx(self, path: Path) -> str:
        try:
            import docx  # type: ignore
        except ImportError as exc:
            raise RuntimeError("python-docx is required for DOCX extraction") from exc
        doc = docx.Document(str(path))
        parts: List[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text for cell in row.cells]
                parts.append(" | ".join(cells))
        return "\n".join(parts)

    def _extract_xlsx(self, path: Path) -> str:
        try:
            import openpyxl  # type: ignore
        except ImportError as exc:
            raise RuntimeError("openpyxl is required for XLSX extraction") from exc
        wb = openpyxl.load_workbook(str(path), data_only=True)
        parts: List[str] = []
        for sheet in wb.worksheets:
            parts.append(f"Sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)

    def _extract_pptx(self, path: Path) -> str:
        try:
            from pptx import Presentation  # type: ignore
        except ImportError as exc:
            raise RuntimeError("python-pptx is required for PPTX extraction") from exc
        prs = Presentation(str(path))
        parts: List[str] = []
        for slide_idx, slide in enumerate(prs.slides, start=1):
            parts.append(f"Slide {slide_idx}:")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = "".join(run.text for run in para.runs)
                        if text.strip():
                            parts.append(text)
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------
    def _chunk_text(
        self,
        text: str,
        filename: str,
        content_hash: str,
        project_id: Optional[str],
        language: str,
        page_map: Optional[Dict[int, str]] = None,
    ) -> List[DocumentChunk]:
        text = text.strip()
        if not text:
            return []

        chunks: List[DocumentChunk] = []
        start = 0
        idx = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            # Try to break at sentence or paragraph boundary
            if end < text_len:
                for sep in ["\n\n", "\n", ". ", "! ", "? ", "。 ", "؟ "]:
                    sep_idx = text.rfind(sep, start, end)
                    if sep_idx != -1 and sep_idx > start:
                        end = sep_idx + len(sep)
                        break
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = hashlib.sha256(
                    f"{content_hash}:{start}:{end}".encode("utf-8")
                ).hexdigest()[:32]
                chunk_metadata: Dict[str, Any] = {
                    "content_hash": content_hash,
                    "chunk_index": idx,
                    "start_char": start,
                    "end_char": end,
                }
                # Preserve page/section info when available
                if page_map:
                    chunk_metadata["page_map"] = page_map
                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        content=chunk_text,
                        filename=filename,
                        language=language,
                        project_id=project_id,
                        metadata=chunk_metadata,
                    )
                )
                idx += 1
            start = end
            if start < text_len and end - start < self.chunk_overlap:
                start = max(start - self.chunk_overlap, start)

        return chunks

    def _hash_file(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # File type extractors
    # ------------------------------------------------------------------
    def _extract_pdf(self, path: Path) -> str:
        try:
            import pypdf  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pypdf is required for PDF extraction") from exc
        reader = pypdf.PdfReader(str(path))
        parts: List[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)

    def _extract_docx(self, path: Path) -> str:
        try:
            import docx  # type: ignore
        except ImportError as exc:
            raise RuntimeError("python-docx is required for DOCX extraction") from exc
        doc = docx.Document(str(path))
        parts: List[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text for cell in row.cells]
                parts.append(" | ".join(cells))
        return "\n".join(parts)

    def _extract_xlsx(self, path: Path) -> str:
        try:
            import openpyxl  # type: ignore
        except ImportError as exc:
            raise RuntimeError("openpyxl is required for XLSX extraction") from exc
        wb = openpyxl.load_workbook(str(path), data_only=True)
        parts: List[str] = []
        for sheet in wb.worksheets:
            parts.append(f"Sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)

    def _extract_pptx(self, path: Path) -> str:
        try:
            from pptx import Presentation  # type: ignore
        except ImportError as exc:
            raise RuntimeError("python-pptx is required for PPTX extraction") from exc
        prs = Presentation(str(path))
        parts: List[str] = []
        for slide_idx, slide in enumerate(prs.slides, start=1):
            parts.append(f"Slide {slide_idx}:")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = "".join(run.text for run in para.runs)
                        if text.strip():
                            parts.append(text)
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------
    def _chunk_text(
        self,
        text: str,
        filename: str,
        content_hash: str,
        project_id: Optional[str],
        language: str,
    ) -> List[DocumentChunk]:
        text = text.strip()
        if not text:
            return []

        chunks: List[DocumentChunk] = []
        start = 0
        idx = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            # Try to break at sentence or paragraph boundary
            if end < text_len:
                for sep in ["\n\n", "\n", ". ", "! ", "? ", "। ", "؟ "]:
                    sep_idx = text.rfind(sep, start, end)
                    if sep_idx != -1 and sep_idx > start:
                        end = sep_idx + len(sep)
                        break
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = hashlib.sha256(
                    f"{content_hash}:{start}:{end}".encode("utf-8")
                ).hexdigest()[:32]
                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        content=chunk_text,
                        filename=filename,
                        language=language,
                        project_id=project_id,
                        metadata={
                            "content_hash": content_hash,
                            "chunk_index": idx,
                            "start_char": start,
                            "end_char": end,
                        },
                    )
                )
                idx += 1
            start = end
            if start < text_len and end - start < self.chunk_overlap:
                start = max(start - self.chunk_overlap, start)

        return chunks

    def _hash_file(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()
