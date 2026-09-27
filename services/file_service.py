from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={".png",".jpg",".jpeg",".pdf",".txt",".md"}


def save_upload(pid,uploaded):
    suffix=Path(uploaded.name).suffix.lower()
    if suffix not in ALLOWED: raise ValueError("Supported formats: PNG, JPG, PDF, TXT, and Markdown.")
    folder=ROOT/"data"/"projects"/str(pid)/"files"; folder.mkdir(parents=True,exist_ok=True)
    # Keep the original display name in metadata while avoiding path traversal.
    safe_name=Path(uploaded.name).name
    target=folder/(safe_name)
    if target.exists(): target=folder/f"{target.stem}_{__import__('uuid').uuid4().hex[:8]}{suffix}"
    target.write_bytes(uploaded.getvalue())
    storage_path = ""
    from . import database_service
    if database_service.is_configured():
        storage_path = database_service.upload_file(pid, safe_name, uploaded.getvalue())
    text=""
    if suffix in {".txt",".md"}: text=target.read_text(encoding="utf-8",errors="replace")
    elif suffix==".pdf":
        try:
            from pypdf import PdfReader
            text="\n".join(page.extract_text() or "" for page in PdfReader(str(target)).pages)
        except Exception: text=""
    return target,text,storage_path
