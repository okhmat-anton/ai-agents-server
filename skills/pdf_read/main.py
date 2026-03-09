import os

async def execute(file_path=None, url=None, pages="all", max_chars=10000):
    """Extract text from PDF files. Tries PyMuPDF (fitz) first, falls back to basic extraction."""
    if not file_path and not url:
        return {"error": "Either file_path or url is required"}
    if url and not file_path:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        file_path = "/tmp/_skill_pdf_temp.pdf"
        with open(file_path, "wb") as f:
            f.write(resp.content)
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    text = ""
    page_count = 0
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page_count = len(doc)
        if pages == "all":
            page_nums = range(page_count)
        elif "-" in str(pages):
            start, end = pages.split("-")
            page_nums = range(int(start) - 1, min(int(end), page_count))
        else:
            page_nums = [int(pages) - 1]
        for i in page_nums:
            if i < page_count:
                text += doc[i].get_text() + "\n"
        doc.close()
    except ImportError:
        with open(file_path, "rb") as f:
            raw = f.read()
        import re
        chunks = re.findall(rb"\(([^)]+)\)", raw)
        text = b" ".join(chunks).decode("latin-1", errors="replace")
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)
    text = text[:max_chars]
    return {"text": text, "length": len(text), "pages": page_count}
