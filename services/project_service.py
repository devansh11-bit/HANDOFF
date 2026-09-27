import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "handoff.sqlite3"


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, filename TEXT NOT NULL, file_type TEXT NOT NULL, path TEXT NOT NULL, extracted_text TEXT DEFAULT '', uploaded_at TEXT NOT NULL, analysis_status TEXT NOT NULL DEFAULT 'Pending', analysis_error TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memory_items(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, category TEXT NOT NULL, content TEXT NOT NULL, source TEXT DEFAULT '', confidence REAL DEFAULT 1, created_at TEXT NOT NULL, UNIQUE(project_id,category,content));
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, title TEXT NOT NULL, description TEXT DEFAULT '', reason TEXT DEFAULT '', source TEXT DEFAULT '', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending', assignee TEXT DEFAULT '', source TEXT DEFAULT '', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, event_type TEXT NOT NULL, description TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS project_members(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, member_name TEXT NOT NULL, member_identifier TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'member', joined_at TEXT NOT NULL, UNIQUE(project_id,member_identifier));
        """)
        for table, fields in {
            "projects": {"project_code": "TEXT", "owner_name": "TEXT NOT NULL DEFAULT 'You'"},
            "messages": {"member_name": "TEXT NOT NULL DEFAULT 'You'"},
            "files": {"created_by": "TEXT NOT NULL DEFAULT 'You'"},
            "decisions": {"added_by": "TEXT NOT NULL DEFAULT 'You'"},
            "tasks": {"created_by": "TEXT NOT NULL DEFAULT 'You'", "completed_by": "TEXT"},
            "activity": {"member_name": "TEXT NOT NULL DEFAULT 'You'"},
            "memory_items": {"created_by": "TEXT NOT NULL DEFAULT 'You'"},
        }.items():
            existing = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
            for column, definition in fields.items():
                if column not in existing:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_project_code ON projects(project_code) WHERE project_code IS NOT NULL")
        columns={row[1] for row in db.execute("PRAGMA table_info(files)")}
        if "analysis_status" not in columns:
            db.execute("ALTER TABLE files ADD COLUMN analysis_status TEXT NOT NULL DEFAULT 'Pending'")
        if "analysis_error" not in columns:
            db.execute("ALTER TABLE files ADD COLUMN analysis_error TEXT DEFAULT ''")


def record(db, pid, event, description, member_name="You"):
    db.execute("INSERT INTO activity(project_id,event_type,description,created_at,member_name) VALUES(?,?,?,?,?)", (pid,event,description,now(),member_name))
    db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now(),pid))


def _shared():
    from . import database_service
    return database_service.is_configured()


def create_project(name, description, member_name="You"):
    if _shared():
        from .database_service import create_project as create_shared_project
        return create_shared_project(name, description, member_name)
    with connect() as db:
        code = "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6))
        t=now(); cur=db.execute("INSERT INTO projects(name,description,created_at,updated_at,project_code,owner_name) VALUES(?,?,?,?,?,?)",(name.strip(),description.strip(),t,t,code,member_name))
        pid=cur.lastrowid
        db.execute("INSERT INTO project_members(project_id,member_name,member_identifier,role,joined_at) VALUES(?,?,?,?,?)",(pid,member_name,secrets.token_hex(12),"owner",t))
        record(db,pid,"PROJECT_CREATED",f"Project created: {name.strip()}",member_name)
        for folder in (ROOT/"data"/"projects"/str(pid)/"files",ROOT/"data"/"projects"/str(pid)/"extracted"):
            folder.mkdir(parents=True,exist_ok=True)
        return pid


def get_projects():
    if _shared():
        from .database_service import projects
        return projects()
    with connect() as db: return [dict(r) for r in db.execute("SELECT * FROM projects ORDER BY updated_at DESC")]


def get_project(pid):
    if _shared():
        from .database_service import project
        return project(pid)
    with connect() as db:
        r=db.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchone(); return dict(r) if r else None


def get_rows(table, pid, limit=100):
    allowed={"files":"uploaded_at","messages":"created_at","memory_items":"created_at","decisions":"created_at","tasks":"created_at","activity":"created_at"}
    if table not in allowed: raise ValueError("Unknown table")
    if _shared():
        from .database_service import rows
        return rows(table, pid, limit)
    with connect() as db: return [dict(r) for r in db.execute(f"SELECT * FROM {table} WHERE project_id=? ORDER BY {allowed[table]} DESC LIMIT ?",(pid,limit))]


def save_memory(pid, category, content, source="", confidence=1, member_name="You"):
    if _shared():
        from .database_service import save_memory as save_shared_memory
        return save_shared_memory(pid, category, content, source, confidence, member_name)
    if not str(content).strip(): return
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO memory_items(project_id,category,content,source,confidence,created_at,created_by) VALUES(?,?,?,?,?,?,?)",(pid,category,str(content).strip(),source,float(confidence or 0),now(),member_name))
        record(db,pid,"MEMORY_UPDATED",f"Added {category.lower()} context",member_name)


def save_decision(pid,title,description="",reason="",source="project_chat",member_name="You"):
    if _shared():
        from .database_service import save_decision as save_shared_decision
        return save_shared_decision(pid,title,description,reason,source,member_name)
    with connect() as db:
        db.execute("INSERT INTO decisions(project_id,title,description,reason,source,created_at,added_by) VALUES(?,?,?,?,?,?,?)",(pid,title.strip(),description.strip(),reason.strip(),source,now(),member_name))
        if title.strip(): db.execute("INSERT OR IGNORE INTO memory_items(project_id,category,content,source,confidence,created_at) VALUES(?,?,?,?,?,?)",(pid,"Decisions",title.strip()+(" — "+reason.strip() if reason.strip() else ""),source,1,now()))
        record(db,pid,"DECISION_ADDED",title.strip(),member_name)


def save_task(pid,title,status="Pending",assignee="",source="user",member_name="You"):
    if _shared():
        from .database_service import save_task as save_shared_task
        return save_shared_task(pid,title,status,assignee,source,member_name)
    with connect() as db:
        db.execute("INSERT INTO tasks(project_id,title,status,assignee,source,created_at,created_by) VALUES(?,?,?,?,?,?,?)",(pid,title.strip(),status,assignee.strip(),source,now(),member_name))
        record(db,pid,"TASK_CREATED",title.strip(),member_name)


def update_task(task_id,status,pid,member_name="You"):
    if _shared():
        from .database_service import update_task as update_shared_task
        return update_shared_task(task_id,status,pid,member_name)
    with connect() as db:
        db.execute("UPDATE tasks SET status=?,completed_by=? WHERE id=? AND project_id=?",(status,member_name if status=="Completed" else None,task_id,pid))
        record(db,pid,"TASK_COMPLETED" if status=="Completed" else "TASK_UPDATED",f"Task marked {status}",member_name)


def save_message(pid,role,content,member_name="You"):
    if _shared():
        from .database_service import save_message as save_shared_message
        return save_shared_message(pid,role,content,member_name)
    with connect() as db:
        db.execute("INSERT INTO messages(project_id,role,content,created_at,member_name) VALUES(?,?,?,?,?)",(pid,role,content,now(),member_name))
        if role=="user": record(db,pid,"MESSAGE_ADDED",f"{member_name}: Project chat updated",member_name)


def add_file(pid,filename,file_type,path,text,analysis_status="Pending",member_name="You"):
    if _shared():
        from .database_service import add_file as add_shared_file
        return add_shared_file(pid,filename,file_type,path,text,analysis_status,member_name)
    with connect() as db:
        cursor=db.execute("INSERT INTO files(project_id,filename,file_type,path,extracted_text,uploaded_at,analysis_status,created_by) VALUES(?,?,?,?,?,?,?,?)",(pid,filename,file_type,path,text,now(),analysis_status,member_name))
        record(db,pid,"FILE_UPLOADED",f"Uploaded {filename}",member_name)
        return cursor.lastrowid


def update_file_analysis(file_id,pid,status,error=""):
    if _shared():
        from .database_service import update_file_analysis as update_shared_file_analysis
        return update_shared_file_analysis(file_id,pid,status,error)
    with connect() as db:
        db.execute("UPDATE files SET analysis_status=?,analysis_error=? WHERE id=? AND project_id=?",(status,error,file_id,pid))


def get_project_by_code(code):
    if _shared():
        from .database_service import project_by_code
        return project_by_code(code)
    with connect() as db:
        row = db.execute("SELECT * FROM projects WHERE project_code=?", (code.strip().upper(),)).fetchone()
        return dict(row) if row else None


def join_project(code, member_name):
    if _shared():
        from .database_service import join_project as join_shared_project
        return join_shared_project(code, member_name)
    p = get_project_by_code(code)
    if not p: return None
    with connect() as db:
        existing = db.execute("SELECT 1 FROM project_members WHERE project_id=? AND lower(member_name)=lower(?)", (p["id"], member_name.strip())).fetchone()
        if not existing:
            db.execute("INSERT INTO project_members(project_id,member_name,member_identifier,role,joined_at) VALUES(?,?,?,?,?)",(p["id"],member_name.strip(),secrets.token_hex(12),"member",now()))
            record(db,p["id"],"MEMBER_JOINED",f"{member_name.strip()} joined the project",member_name.strip())
    return p


def get_project_members(project_id):
    """Return this project's members as dictionaries, or [] when it has none."""
    if _shared():
        from .database_service import members
        return members(project_id) or []
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM project_members WHERE project_id=? ORDER BY joined_at", (project_id,))]


def add_activity(pid, event_type, description, member_name="You"):
    if _shared():
        from .database_service import record as record_shared
        return record_shared(pid, event_type, description, member_name)
    with connect() as db:
        record(db, pid, event_type, description, member_name)
