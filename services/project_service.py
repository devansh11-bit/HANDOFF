import sqlite3
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
        """)
        columns={row[1] for row in db.execute("PRAGMA table_info(files)")}
        if "analysis_status" not in columns:
            db.execute("ALTER TABLE files ADD COLUMN analysis_status TEXT NOT NULL DEFAULT 'Pending'")
        if "analysis_error" not in columns:
            db.execute("ALTER TABLE files ADD COLUMN analysis_error TEXT DEFAULT ''")


def record(db, pid, event, description):
    db.execute("INSERT INTO activity(project_id,event_type,description,created_at) VALUES(?,?,?,?)", (pid,event,description,now()))
    db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now(),pid))


def create_project(name, description):
    with connect() as db:
        t=now(); cur=db.execute("INSERT INTO projects(name,description,created_at,updated_at) VALUES(?,?,?,?)",(name.strip(),description.strip(),t,t))
        pid=cur.lastrowid; record(db,pid,"PROJECT_CREATED",f"Project created: {name.strip()}")
        for folder in (ROOT/"data"/"projects"/str(pid)/"files",ROOT/"data"/"projects"/str(pid)/"extracted"):
            folder.mkdir(parents=True,exist_ok=True)
        return pid


def get_projects():
    with connect() as db: return [dict(r) for r in db.execute("SELECT * FROM projects ORDER BY updated_at DESC")]


def get_project(pid):
    with connect() as db:
        r=db.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchone(); return dict(r) if r else None


def get_rows(table, pid, limit=100):
    allowed={"files":"uploaded_at","messages":"created_at","memory_items":"created_at","decisions":"created_at","tasks":"created_at","activity":"created_at"}
    if table not in allowed: raise ValueError("Unknown table")
    with connect() as db: return [dict(r) for r in db.execute(f"SELECT * FROM {table} WHERE project_id=? ORDER BY {allowed[table]} DESC LIMIT ?",(pid,limit))]


def save_memory(pid, category, content, source="", confidence=1):
    if not str(content).strip(): return
    with connect() as db: db.execute("INSERT OR IGNORE INTO memory_items(project_id,category,content,source,confidence,created_at) VALUES(?,?,?,?,?,?)",(pid,category,str(content).strip(),source,float(confidence or 0),now()))


def save_decision(pid,title,description="",reason="",source="project_chat"):
    with connect() as db:
        db.execute("INSERT INTO decisions(project_id,title,description,reason,source,created_at) VALUES(?,?,?,?,?,?)",(pid,title.strip(),description.strip(),reason.strip(),source,now()))
        if title.strip(): db.execute("INSERT OR IGNORE INTO memory_items(project_id,category,content,source,confidence,created_at) VALUES(?,?,?,?,?,?)",(pid,"Decisions",title.strip()+(" — "+reason.strip() if reason.strip() else ""),source,1,now()))
        record(db,pid,"DECISION_ADDED",title.strip())


def save_task(pid,title,status="Pending",assignee="",source="user"):
    with connect() as db:
        db.execute("INSERT INTO tasks(project_id,title,status,assignee,source,created_at) VALUES(?,?,?,?,?,?)",(pid,title.strip(),status,assignee.strip(),source,now()))
        record(db,pid,"TASK_CREATED",title.strip())


def update_task(task_id,status,pid):
    with connect() as db:
        db.execute("UPDATE tasks SET status=? WHERE id=? AND project_id=?",(status,task_id,pid))
        record(db,pid,"TASK_COMPLETED" if status=="Completed" else "TASK_UPDATED",f"Task marked {status}")


def save_message(pid,role,content):
    with connect() as db:
        db.execute("INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)",(pid,role,content,now()))
        if role=="user": record(db,pid,"MESSAGE_ADDED","Project chat updated")


def add_file(pid,filename,file_type,path,text,analysis_status="Pending"):
    with connect() as db:
        cursor=db.execute("INSERT INTO files(project_id,filename,file_type,path,extracted_text,uploaded_at,analysis_status) VALUES(?,?,?,?,?,?,?)",(pid,filename,file_type,path,text,now(),analysis_status))
        record(db,pid,"FILE_UPLOADED",f"Uploaded {filename}")
        return cursor.lastrowid


def update_file_analysis(file_id,pid,status,error=""):
    with connect() as db:
        db.execute("UPDATE files SET analysis_status=?,analysis_error=? WHERE id=? AND project_id=?",(status,error,file_id,pid))
