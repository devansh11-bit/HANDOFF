"""Optional Supabase persistence for shared HANDOFF projects.

SQLite remains the zero-configuration local backend. Supabase access is
centralized here so application pages use the same project_service API.
"""
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def is_configured():
    return bool(os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")))


def check_connection():
    """Check the configured shared backend without exposing exception details."""
    if not is_configured():
        return False
    try:
        client().table("projects").select("id").limit(1).execute()
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def client():
    if not is_configured():
        return None
    from supabase import create_client
    raw_url = os.environ["SUPABASE_URL"].strip().rstrip("/")
    parsed = urlsplit(raw_url)
    # The Python SDK expects the project root URL, not the REST endpoint.
    path = parsed.path[:-len("/rest/v1")] if parsed.path.endswith("/rest/v1") else parsed.path
    project_url = urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
    api_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]).strip()
    return create_client(project_url, api_key)


def _data(response):
    return response.data or []


def rows(table, pid, limit=100):
    sort_column = "uploaded_at" if table == "files" else "created_at"
    return _data(client().table(table).select("*").eq("project_id", str(pid)).order(sort_column, desc=True).limit(limit).execute())


def projects():
    return _data(client().table("projects").select("*").order("updated_at", desc=True).execute())


def project(pid):
    values = _data(client().table("projects").select("*").eq("id", str(pid)).limit(1).execute())
    if not values:
        return None
    result = values[0]
    if not result.get("owner_name"):
        team = members(pid)
        if team:
            result["owner_name"] = team[0].get("member_name", "You")
    return result


def project_by_code(code):
    values = _data(client().table("projects").select("*").eq("project_code", code.upper().strip()).limit(1).execute())
    return values[0] if values else None


def members(pid):
    return _data(client().table("project_members").select("*").eq("project_id", str(pid)).order("joined_at").execute())


def insert(table, values):
    return _data(client().table(table).insert(values).execute())


def insert_with_actor(table, values, member_name):
    """Store attribution in whichever optional actor field the existing table has."""
    for field in ("member_name", "created_by", "added_by"):
        candidate = dict(values, **{field: member_name})
        try:
            return insert(table, candidate)
        except Exception as exc:
            message = str(exc)
            if "PGRST204" in message and f"'{field}' column" in message:
                continue
            raise
    return insert(table, values)


def update(table, values, **filters):
    query = client().table(table).update(values)
    for key, value in filters.items():
        query = query.eq(key, str(value))
    return _data(query.execute())


def record(pid, event_type, description, member_name="You"):
    insert("activity", {"project_id": str(pid), "event_type": event_type, "description": description, "member_name": member_name})
    update("projects", {"updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}, id=pid)


def create_project(name, description, member_name="You"):
    import secrets
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    for _ in range(10):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        try:
            created = insert("projects", {"name": name.strip(), "description": description.strip(), "project_code": code})
        except Exception:
            if project_by_code(code):
                continue
            raise
        p = created[0] if created else project_by_code(code)
        if not p:
            raise RuntimeError("Supabase created the project but did not return its project id.")
        insert("project_members", {"project_id": str(p["id"]), "member_name": member_name, "member_identifier": secrets.token_hex(12)})
        record(p["id"], "PROJECT_CREATED", f"Project created: {name.strip()}", member_name)
        return p["id"]
    raise RuntimeError("Could not allocate a unique project code. Try again.")


def join_project(code, member_name):
    p = project_by_code(code)
    if not p:
        return None
    existing = [m for m in members(p["id"]) if m.get("member_name", "").casefold() == member_name.strip().casefold()]
    if not existing:
        import secrets
        insert("project_members", {"project_id": str(p["id"]), "member_name": member_name.strip(), "member_identifier": secrets.token_hex(12)})
        record(p["id"], "MEMBER_JOINED", f"{member_name.strip()} joined the project", member_name.strip())
    return p


def save_memory(pid, category, content, source="", confidence=1, member_name="You"):
    if str(content).strip():
        try:
            insert_with_actor("memory_items", {"project_id": str(pid), "category": category, "content": str(content).strip(), "source": source, "confidence": float(confidence or 0)}, member_name)
            record(pid, "MEMORY_UPDATED", f"Added {category.lower()} context", member_name)
        except Exception as exc:
            if "duplicate" not in str(exc).lower() and "unique" not in str(exc).lower():
                raise


def save_decision(pid, title, description="", reason="", source="project_chat", member_name="You"):
    insert_with_actor("decisions", {"project_id": str(pid), "title": title.strip(), "description": description.strip(), "reason": reason.strip(), "source": source}, member_name)
    if title.strip(): save_memory(pid, "Decisions", title.strip() + (" — " + reason.strip() if reason.strip() else ""), source, member_name=member_name)
    record(pid, "DECISION_ADDED", title.strip(), member_name)


def save_task(pid, title, status="Pending", assignee="", source="user", member_name="You"):
    insert_with_actor("tasks", {"project_id": str(pid), "title": title.strip(), "status": status, "assignee": assignee.strip(), "source": source}, member_name)
    record(pid, "TASK_CREATED", title.strip(), member_name)


def update_task(task_id, status, pid, member_name="You"):
    try:
        update("tasks", {"status": status, "completed_by": member_name if status == "Completed" else None}, id=task_id, project_id=pid)
    except Exception as exc:
        message = str(exc)
        if "PGRST204" not in message or "'completed_by' column" not in message:
            raise
        update("tasks", {"status": status}, id=task_id, project_id=pid)
    record(pid, "TASK_COMPLETED" if status == "Completed" else "TASK_UPDATED", f"Task marked {status}", member_name)


def save_message(pid, role, content, member_name="You"):
    insert("messages", {"project_id": str(pid), "role": role, "content": content, "member_name": member_name})
    if role == "user": record(pid, "MESSAGE_ADDED", f"{member_name}: Project chat updated", member_name)


def add_file(pid, filename, file_type, path, text, analysis_status="Pending", member_name="You"):
    result = insert_with_actor("files", {"project_id": str(pid), "filename": filename, "file_type": file_type, "path": path, "extracted_text": text, "analysis_status": analysis_status}, member_name)
    record(pid, "FILE_UPLOADED", f"Uploaded {filename}", member_name)
    return result[0]["id"]


def update_file_analysis(file_id, pid, status, error=""):
    update("files", {"analysis_status": status, "analysis_error": error}, id=file_id, project_id=pid)


def upload_file(pid, filename, data):
    import uuid
    safe = filename.replace("\\", "_").replace("/", "_")
    object_path = f"projects/{pid}/{uuid.uuid4().hex}_{safe}"
    client().storage.from_("project-files").upload(
        object_path, data,
        file_options={"upsert": "true", "content-type": "application/octet-stream"},
    )
    return object_path


def download_file(object_path):
    return client().storage.from_("project-files").download(object_path)
