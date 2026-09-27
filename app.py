from pathlib import Path
import os

import streamlit as st

from services import project_service as db
from services.file_service import save_upload
from services.gemini_service import GeminiService
from services.handoff_service import fallback_handoff
from services.memory_service import build_context, store_extraction
from services import database_service


ROOT = Path(__file__).resolve().parent
PAGES = ["Overview", "Files", "Project Chat", "Memory", "Tasks", "Activity"]
DOCS = {
    "Product Requirements": "HANDOFF_PRD.md",
    "Design & Architecture": "HANDOFF_DESIGN.md",
    "Technical Stack": "HANDOFF_TECH_STACK.md",
}

st.set_page_config(page_title="HANDOFF", page_icon="↗", layout="wide")
st.markdown(
    """<style>
    [data-testid="stAppViewContainer"] { background: #f5f7f8; }
    [data-testid="stSidebar"] { background: #132431; }
    .stApp [data-testid="stSidebar"] * { color: #edf3f4 !important; }
    .stApp [data-testid="stSidebar"] [role="combobox"], .stApp [data-testid="stSidebar"] [role="combobox"] * { color: #172631 !important; background: #ffffff !important; }
    .stApp [data-testid="stSidebar"] input, .stApp [data-testid="stSidebar"] textarea { color: #172631 !important; background: #ffffff !important; }
    [data-testid="stAppViewContainer"] * { color: #172631; }
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        background: #203746; border-color: #395160; color: #f5fafb;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
        background: #54c4a5; border-color: #54c4a5; color: #10251f;
    }
    .stButton > button { min-height: 2.65rem; border-radius: .65rem; }
    [data-testid="stAppViewContainer"] [data-testid="stBaseButton-secondary"] { background: #ffffff; border-color: #d5dfe3; color: #172631; }
    [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] { background: #197d68; border-color: #197d68; color: #ffffff; }
    div[data-testid="stMetric"] { background: white; padding: .8rem 1rem; border: 1px solid #e4e9ec; border-radius: 12px; }
    .eyebrow { color: #508478; font-size: .75rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
    </style>""",
    unsafe_allow_html=True,
)

db.init_db()
ai = GeminiService()
shared_cloud_connected = database_service.check_connection()
if "member_name" not in st.session_state:
    st.session_state.member_name = "You"
if "member_name_input" not in st.session_state:
    st.session_state.member_name_input = st.session_state.member_name


def clear_project_outputs():
    for key in list(st.session_state):
        if key in {"catchup_result", "handoff_result"} or key.startswith("why_result_"):
            del st.session_state[key]


def set_page(page):
    st.session_state.workspace_page = page


def project_context(pid):
    selected = db.get_project(pid)
    return build_context(selected, pid)


def analyze_file(file_row, pid):
    if not ai.available:
        st.error("Gemini is not connected. Add GEMINI_API_KEY and GEMINI_MODEL to .env.")
        return
    db.update_file_analysis(file_row["id"], pid, "Analyzing")
    try:
        analysis_path = file_row["path"]
        if database_service.is_configured() and not Path(analysis_path).is_file():
            cache = ROOT / "data" / "projects" / str(pid) / "files" / Path(analysis_path).name
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(database_service.download_file(analysis_path))
            analysis_path = str(cache)
        with st.spinner(f"Analyzing {file_row['filename']} with Gemini…"):
            extracted = ai.analyze_project_material(
                file_row["filename"], file_row["extracted_text"] or "", analysis_path
            )
            count = store_extraction(pid, extracted, file_row["filename"])
        db.update_file_analysis(file_row["id"], pid, "Analyzed")
        st.session_state.last_analysis = (file_row["filename"], count)
    except Exception as exc:
        db.update_file_analysis(file_row["id"], pid, "Error", str(exc))
        st.error(f"Gemini could not analyze this file: {exc}")


def ensure_demo_project():
    demo_name = "Smart Waste Management System"
    existing = next((p for p in db.get_projects() if p["name"] == demo_name), None)
    if existing:
        pid = existing["id"]
    else:
        pid = db.create_project(
            demo_name,
            "Build a smart waste-bin monitoring prototype that measures bin fill level and helps teams plan collection.",
        )
        db.save_memory(pid, "Goals", "Monitor waste-bin fill level using an ESP32-based prototype.", "Demo project brief")
        db.save_memory(pid, "Requirements", "Measure bin fill level and support more informed collection planning.", "Demo project brief")
        db.save_memory(pid, "Technology", "ESP32 prototype controller with Wi-Fi connectivity.", "Demo component list")
        db.save_memory(pid, "Important Context", "An ultrasonic distance sensor measures the remaining space in the bin.", "Demo component list")
        db.save_memory(pid, "Completed", "Initial hardware research completed.", "Demo project brief")
        db.save_memory(pid, "Pending", "Prototype assembly, backend integration, and testing remain.", "Demo project brief")
        db.save_decision(
            pid,
            "Use ESP32 for the prototype",
            "Selected as the prototype controller.",
            "It provides Wi-Fi connectivity and sufficient GPIO for the prototype.",
            "Demo requirements meeting",
        )
        db.save_task(pid, "Assemble the sensor prototype", source="Demo project brief")
        db.save_task(pid, "Integrate the backend", source="Demo project brief")
        db.save_task(pid, "Test fill-level readings", source="Demo project brief")

    if not database_service.is_configured() and not db.get_rows("files", pid):
        folder = ROOT / "data" / "projects" / str(pid) / "files"
        folder.mkdir(parents=True, exist_ok=True)
        brief = folder / "smart_waste_demo_brief.txt"
        content = (
            "Smart Waste Management System\n"
            "Objective: Build a prototype that monitors waste-bin fill level.\n"
            "Controller: ESP32, selected for Wi-Fi connectivity and sufficient GPIO.\n"
            "Sensor: Ultrasonic distance sensor.\n"
            "Completed: Initial hardware research.\n"
            "Pending: Assemble the prototype, integrate the backend, and test readings.\n"
        )
        brief.write_text(content, encoding="utf-8")
        db.add_file(pid, brief.name, "txt", str(brief), content)
    return pid


# Sidebar: creation is available from every page, and project switching is scoped to the active ID.
st.sidebar.markdown("# ↗ HANDOFF")
st.sidebar.caption("One project. One shared context.")
if shared_cloud_connected:
    st.sidebar.success("Supabase Database Connected")
elif database_service.is_configured():
    st.sidebar.warning("Supabase is configured but unavailable. Check the client dependency and server credentials.")
else:
    st.sidebar.info("Supabase is not configured.\nShared collaboration is unavailable. Configure SUPABASE_URL and SUPABASE_KEY.")
if "pending_member_name" in st.session_state:
    st.session_state["member_name_input"] = st.session_state.pop("pending_member_name")
st.session_state.member_name = st.sidebar.text_input("Your name for this session", key="member_name_input")
invite_code = st.query_params.get("project", "")
if invite_code or st.session_state.get("show_join_project"):
    st.sidebar.markdown("### JOIN A PROJECT")
    with st.sidebar.form("join_project_form"):
        join_code = st.text_input("Project Code", value=invite_code, key="join_code_input")
        join_name = st.text_input("Your Name", value=st.session_state.member_name, key="join_name_input")
        join_submit = st.form_submit_button("Join Project", type="primary", use_container_width=True)
    if join_submit:
        joined = db.join_project(join_code, join_name.strip())
        if joined:
            st.session_state.member_name = join_name.strip()
            st.session_state.pending_member_name = join_name.strip()
            st.session_state.joined_project_id = joined["id"]
            st.session_state.project_select = joined["id"]
            st.session_state.workspace_page = "Overview"
            st.session_state.show_join_project = False
            st.query_params.clear()
            st.rerun()
        else:
            st.sidebar.error("No project was found for that code.")
if st.sidebar.button("+ Join Project", use_container_width=True, key="join_project_toggle"):
    st.session_state.show_join_project = not st.session_state.get("show_join_project", False)
    st.rerun()
if st.sidebar.button("+ New Project", type="primary", use_container_width=True, key="new_project_toggle"):
    st.session_state.show_new_project = not st.session_state.get("show_new_project", False)

if st.session_state.get("show_new_project", False):
    with st.sidebar.form("create_project_form", clear_on_submit=True):
        st.markdown("### Create New Project")
        new_name = st.text_input("Project Name", placeholder="My project")
        new_description = st.text_area("Description", placeholder="What are you working on?")
        submitted = st.form_submit_button("Create Project", type="primary", use_container_width=True)
    if st.sidebar.button("Cancel", key="cancel_new_project"):
        st.session_state.show_new_project = False
        st.rerun()
    if submitted:
        if not new_name.strip():
            st.sidebar.error("Enter a project name.")
        else:
            new_id = db.create_project(new_name, new_description, st.session_state.member_name.strip() or "You")
            st.session_state.project_select = new_id
            st.session_state.workspace_page = "Overview"
            st.session_state.show_new_project = False
            clear_project_outputs()
            st.session_state.just_created_project = new_id
            st.rerun()

try:
    projects = db.get_projects()
except Exception:
    st.error("Supabase is configured but HANDOFF could not load shared projects. Check the Supabase client and server credentials.")
    st.stop()
if projects:
    st.sidebar.markdown("### YOUR PROJECTS")
    current_id = st.sidebar.selectbox(
        "Your projects",
        options=[p["id"] for p in projects],
        format_func=lambda pid: next(p["name"] for p in projects if p["id"] == pid),
        key="project_select",
        label_visibility="collapsed",
    )
    previous_id = st.session_state.get("active_project_id")
    if previous_id is not None and current_id != previous_id:
        st.session_state.workspace_page = "Overview"
        clear_project_outputs()
    st.session_state.active_project_id = current_id
    project = db.get_project(current_id)
    if project["name"] == "Smart Waste Management System":
        ensure_demo_project()
    st.sidebar.markdown("### WORKSPACE")
    page = st.sidebar.radio(
        "Workspace navigation",
        PAGES,
        key="workspace_page",
        label_visibility="collapsed",
    )
else:
    current_id = None
    project = None
    page = "Overview"

st.sidebar.divider()
if current_id is not None:
    team_members = db.get_project_members(current_id)
    st.sidebar.markdown("### TEAM")
    st.sidebar.caption(f"{len(team_members)} member(s)")
    for team_member in team_members[:5]:
        st.sidebar.write(f"👤 {team_member['member_name']}")
st.sidebar.markdown("### AI ENGINE")
if ai.available:
    st.sidebar.success("Gemini Connected")
    st.sidebar.caption(f"Model: {ai.model}")
else:
    st.sidebar.warning("Gemini Not Connected")
    st.sidebar.caption("Add GEMINI_API_KEY and GEMINI_MODEL to .env.")
with st.sidebar.expander("Powered by Gemini"):
    st.caption("Project material analysis · Project Memory extraction · Project Chat · Catch Me Up · Decision reasoning · Handoff Package")

with st.sidebar.expander("Project Documentation"):
    doc_name = st.selectbox("Choose a document", list(DOCS), label_visibility="collapsed")
    st.markdown((ROOT / DOCS[doc_name]).read_text(encoding="utf-8"))


def page_header(kicker, title, detail):
    st.markdown(f'<div class="eyebrow">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    if detail:
        st.caption(detail)


if not projects:
    st.markdown('<div class="eyebrow">PROJECT CONTINUITY WORKSPACE</div>', unsafe_allow_html=True)
    st.title("One project. One shared context.")
    st.write("Create a workspace, add the material your team already has, and let HANDOFF build a shared project memory.")
    left, right = st.columns([1.3, 1])
    with left, st.container(border=True):
        st.subheader("Welcome to your project")
        st.write("Your shared project context starts here.")
        st.markdown("1. Upload your project material\n2. Let Gemini understand it\n3. Review Project Memory\n4. Continue the work with Project Chat")
        if st.button("+ New Project", type="primary", key="welcome_new_project"):
            st.session_state.show_new_project = True
            st.rerun()
    with right, st.container(border=True):
        st.subheader("Explore the demo")
        st.write("Open the Smart Waste project with example context, a recorded ESP32 decision, and tasks.")
        if st.button("Open Smart Waste demo", key="create_demo"):
            pid = ensure_demo_project()
            st.session_state.project_select = pid
            st.session_state.workspace_page = "Overview"
            st.rerun()
    st.stop()

if st.session_state.get("just_created_project") == current_id:
    st.success(f"Project created: {project['name']} · Project Code: {project.get('project_code', 'Unavailable')}. Share the code or link with teammates.")
    st.session_state.pop("just_created_project", None)
if st.session_state.get("joined_project_id") == current_id:
    st.success(f"✓ Joined project · {project['name']}")
    st.session_state.pop("joined_project_id", None)

context = project_context(current_id)

if page == "Overview":
    st.markdown('<div class="eyebrow">PROJECT OVERVIEW</div>', unsafe_allow_html=True)
    st.title(project["name"])
    st.write(project["description"] or "Add project material to create a shared context for your team.")
    members = db.get_project_members(current_id)
    with st.container(border=True):
        st.subheader("Team")
        owner_name = project.get("owner_name") or (members[0]["member_name"] if members else "Not set")
        st.caption(f"Owner · {owner_name} · {len(members)} member(s)")
        st.write(" · ".join(f"👤 {member['member_name']}" for member in members) or "No members yet")
        code = project.get("project_code", "")
        base_url = os.getenv("HANDOFF_BASE_URL", "").strip()
        if not base_url:
            try:
                base_url = st.context.url.split("?", 1)[0]
            except Exception:
                base_url = ""
        share_link = f"{base_url}?project={code}" if base_url and code else ""
        if code:
            st.markdown("**Project Code**")
            st.code(code)
            st.caption("Share this code with teammates.")
        if share_link:
            st.markdown("**Share Link**")
            st.code(share_link)
            st.caption("Copy the link above and send it to your teammates.")
    tasks = db.get_rows("tasks", current_id)
    decisions = db.get_rows("decisions", current_id)
    files = db.get_rows("files", current_id)
    completed_count = sum(task["status"] == "Completed" for task in tasks)
    progress = int(completed_count / len(tasks) * 100) if tasks else 0
    metrics = st.columns(4)
    metrics[0].metric("Progress", f"{progress}%")
    metrics[1].metric("Open Tasks", sum(task["status"] != "Completed" for task in tasks))
    metrics[2].metric("Decisions", len(decisions))
    metrics[3].metric("Project Files", len(files))

    action_cols = st.columns(3)
    catchup_clicked = action_cols[0].button("⚡ Catch Me Up", type="primary", use_container_width=True)
    action_cols[1].button("💬 Ask Project AI", use_container_width=True, on_click=set_page, args=("Project Chat",))
    handoff_clicked = action_cols[2].button("📦 Generate Handoff", use_container_width=True)
    if catchup_clicked:
        if not ai.available:
            st.session_state.catchup_result = None
            st.error("Gemini is not connected. Add GEMINI_API_KEY and GEMINI_MODEL to .env.")
        else:
            try:
                st.session_state.catchup_result = {"text": ai.generate_catchup(context), "generated": True}
            except Exception as exc:
                st.session_state.catchup_result = None
                st.error(f"Gemini could not generate a catch-up: {exc}")
    if handoff_clicked:
        if ai.available:
            try:
                st.session_state.handoff_result = {"text": ai.generate_handoff(context), "generated": True}
            except Exception as exc:
                st.session_state.handoff_result = {"text": fallback_handoff(project, current_id), "generated": False}
                st.warning(f"Gemini could not generate the package. Showing one from recorded project memory instead. ({exc})")
        else:
            st.session_state.handoff_result = {"text": fallback_handoff(project, current_id), "generated": False}

    catchup_result = st.session_state.get("catchup_result")
    if catchup_result:
        with st.container(border=True):
            st.subheader("Catch Me Up")
            st.markdown(catchup_result["text"])
            if catchup_result["generated"]:
                st.caption("Generated by Gemini · Based on current project memory and recent activity")
    handoff_result = st.session_state.get("handoff_result")
    if handoff_result:
        with st.container(border=True):
            st.subheader("Handoff Package")
            if handoff_result["generated"]:
                st.caption("Generated by Gemini · Grounded in project memory")
            else:
                st.caption("Generated from recorded project memory · Gemini did not generate this package")
            st.markdown(handoff_result["text"])
            st.download_button(
                "Download Handoff Package",
                handoff_result["text"],
                file_name="project-handoff.md",
                mime="text/markdown",
            )

    if not files and not db.get_rows("memory_items", current_id):
        with st.container(border=True):
            st.subheader("Your shared project context starts here")
            st.write("Upload project material. Gemini can extract goals, requirements, decisions, tasks, and open questions into Project Memory.")
            st.markdown("**Upload → Gemini analysis → Project Memory → Project Chat**")
            st.button("Upload Project Material", type="primary", key="empty_upload", on_click=set_page, args=("Files",))

    work_col, decision_col = st.columns(2)
    with work_col, st.container(border=True):
        st.subheader("Pending Work")
        pending = [task for task in tasks if task["status"] != "Completed"]
        if pending:
            for task in pending[:6]:
                st.markdown(f"- **{task['title']}** · {task['status']}")
        else:
            st.caption("No tasks yet. Tasks will appear here as they’re added or extracted from project material.")
    with decision_col, st.container(border=True):
        st.subheader("Recent Decisions")
        if decisions:
            for item in decisions[:5]:
                author = item.get("member_name") or item.get("created_by") or item.get("added_by")
                byline = f" · Added by {author}" if author else ""
                st.markdown(f"- **{item['title']}** — {item['reason'] or 'Reason not recorded'}{byline}")
        else:
            st.caption("No decisions recorded yet.")
    with st.container(border=True):
        st.subheader("Recent Activity")
        activities = db.get_rows("activity", current_id, 6)
        if activities:
            for item in activities:
                st.caption(f"{item.get('member_name', 'Member')} · {item['created_at'][:16].replace('T', ' ')} · {item['description']}")
        else:
            st.caption("No activity yet. Project changes will appear here.")

elif page == "Files":
    page_header("PROJECT FILES", "Project Files", "Upload project material and build your shared Project Memory.")
    if ai.available:
        st.info(f"Gemini is ready · Model: {ai.model}")
    else:
        st.warning("Gemini is not connected. Files can be stored now; add GEMINI_API_KEY and GEMINI_MODEL to .env to analyze them.")
    with st.container(border=True):
        st.markdown("**Upload project material**")
        uploads = st.file_uploader(
            "Supported: PDF · PNG · JPG · TXT · MD",
            type=["pdf", "png", "jpg", "jpeg", "txt", "md"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key=f"uploads_{current_id}",
        )
        if st.button("Upload Files", type="primary", disabled=not uploads, key="upload_files"):
            for uploaded in uploads or []:
                try:
                    path, text, storage_path = save_upload(current_id, uploaded)
                    file_id = db.add_file(current_id, uploaded.name, path.suffix.lower().lstrip("."), storage_path or str(path), text, member_name=st.session_state.member_name)
                    if storage_path:
                        st.success(f"Uploaded {uploaded.name} to shared project storage.")
                    if ai.available:
                        row = next(item for item in db.get_rows("files", current_id) if item["id"] == file_id)
                        analyze_file(row, current_id)
                    else:
                        st.success(f"Uploaded {uploaded.name}. It’s ready for Gemini analysis when a key is configured.")
                except Exception as exc:
                    if "row-level security policy" in str(exc).lower():
                        st.error(f"Could not upload {uploaded.name}: private Supabase Storage denied the write. Configure a bucket upload policy or set SUPABASE_SERVICE_ROLE_KEY in server secrets.")
                    else:
                        st.error(f"Could not upload {uploaded.name}: {exc}")
            st.rerun()
    with st.container(border=True):
        st.subheader("How HANDOFF works")
        steps = st.columns(4)
        for col, number, title in zip(
            steps,
            ["01", "02", "03", "04"],
            ["Upload material", "Gemini analyzes it", "Project Memory updates", "Ask your project"],
        ):
            col.markdown(f"**{number} · {title}**")
    st.subheader("Uploaded files")
    files = db.get_rows("files", current_id)
    if not files:
        st.info("No project files yet. Add a requirements document, meeting notes, an image, or a text brief to begin.")
    for file_row in files:
        with st.container(border=True):
            name_col, status_col, action_col = st.columns([3, 2, 1.5])
            name_col.markdown(f"**📄 {file_row['filename']}**")
            name_col.caption(f"{file_row['file_type'].upper()} · Added {file_row['uploaded_at'][:10]} · {file_row.get('created_by') or file_row.get('member_name') or 'Project member'}")
            status = file_row.get("analysis_status", "Pending")
            status_col.write({"Analyzed": "✓ Analyzed by Gemini · Memory updated", "Analyzing": "Analyzing with Gemini…", "Error": "Analysis needs attention", "Pending": "Ready for Gemini analysis"}.get(status, status))
            if status == "Error" and file_row.get("analysis_error"):
                status_col.caption(file_row["analysis_error"])
            if status != "Analyzed" and action_col.button("Analyze with Gemini", key=f"analyze_{file_row['id']}", disabled=not ai.available):
                analyze_file(file_row, current_id)
                st.rerun()
    result = st.session_state.pop("last_analysis", None)
    if result:
        st.success(f"Gemini analysis complete for {result[0]}. Project Memory updated with {result[1]} item(s).")

elif page == "Project Chat":
    page_header("PROJECT CHAT", "Ask Gemini about this project", "Gemini answers from this project’s memory, files, and recent conversation.")
    if ai.available:
        st.success(f"Gemini · {ai.model} · Project context loaded")
    else:
        st.warning("Gemini is not connected. Add GEMINI_API_KEY and GEMINI_MODEL to .env. Chat messages won’t be presented as Gemini answers until it is configured.")
    st.caption("Try: What are we building? · What have we completed? · Why did we choose ESP32? · What is still pending? · What should I work on next?")
    for message in reversed(db.get_rows("messages", current_id, 80)):
        with st.chat_message(message["role"], avatar="↗" if message["role"] == "assistant" else None):
            if message["role"] == "assistant":
                st.caption("Gemini · Project context")
            else:
                st.caption(message.get("member_name", "Member"))
            st.markdown(message["content"])
    question = st.chat_input("Ask about this project…")
    if question:
        db.save_message(current_id, "user", question, st.session_state.member_name)
        if not ai.available:
            st.error("Gemini is not connected. Your question was not answered or labeled as a Gemini response.")
        else:
            try:
                answer = ai.ask_project_question(question, project_context(current_id))
                db.save_message(current_id, "assistant", answer, "Gemini")
            except Exception as exc:
                st.error(f"Gemini could not answer this question: {exc}")
        st.rerun()
    with st.expander("Save a decision or create a task"):
        decision_tab, task_tab = st.tabs(["Decision", "Task"])
        with decision_tab:
            latest_user = next((m["content"] for m in db.get_rows("messages", current_id, 40) if m["role"] == "user"), "")
            with st.form("decision_form"):
                title = st.text_input("Decision", value=latest_user[:160])
                why = st.text_area("Recorded reason (optional)")
                description = st.text_input("Description (optional)")
                if st.form_submit_button("Save decision"):
                    if title.strip():
                        db.save_decision(current_id, title, description, why, member_name=st.session_state.member_name)
                        st.success("Decision added to Project Memory.")
                        st.rerun()
                    else:
                        st.warning("Enter a decision title.")
        with task_tab:
            with st.form("chat_task_form"):
                title = st.text_input("Task")
                assignee = st.text_input("Assignee (optional)")
                if st.form_submit_button("Create task"):
                    if title.strip():
                        db.save_task(current_id, title, assignee=assignee, member_name=st.session_state.member_name)
                        st.rerun()
                    else:
                        st.warning("Enter a task title.")

elif page == "Memory":
    page_header("SHARED PROJECT CONTEXT", "Project Memory", "The shared context HANDOFF remembers for this project.")
    memory = db.get_rows("memory_items", current_id, 250)
    sections = ["Goals", "Requirements", "Technology", "Decisions", "Completed", "Pending", "Important Context", "Open Questions", "Risks / Issues"]
    for category in sections:
        items = [item for item in memory if item["category"] == category]
        with st.container(border=True):
            st.markdown(f"### {category.upper()}")
            if items:
                for item in items:
                    st.markdown(f"- {item['content']}")
                    if item.get("source"):
                        st.caption(f"Source: {item['source']}")
            else:
                st.caption("Nothing recorded yet.")
    st.markdown("### Decisions · Why?")
    decisions = db.get_rows("decisions", current_id)
    if not decisions:
        st.caption("No decisions recorded yet.")
    for decision in decisions:
        with st.container(border=True):
            st.markdown(f"**{decision['title']}**")
            if decision["description"]:
                st.write(decision["description"])
            st.markdown(f"**Recorded reason:** {decision['reason'] or 'The project memory does not contain a recorded reason for this decision.'}")
            st.caption(f"Source: {decision['source'] or 'Not recorded'}")
            result_key = f"why_result_{decision['id']}"
            if st.button("❓ Why?", key=f"why_{decision['id']}"):
                if not ai.available:
                    st.session_state[result_key] = {"text": decision["reason"] or "The project memory does not contain a recorded reason for this decision.", "generated": False}
                else:
                    try:
                        prompt = f"Explain this decision using only recorded evidence. Decision: {decision['title']}. Recorded reason: {decision['reason'] or 'not recorded'}. Include source when available. If reason is absent, say so and do not infer one."
                        st.session_state[result_key] = {"text": ai.ask_project_question(prompt, project_context(current_id)), "generated": True}
                    except Exception as exc:
                        st.session_state[result_key] = {"text": f"Gemini could not explain this decision: {exc}", "generated": False}
            result = st.session_state.get(result_key)
            if result:
                st.info(result["text"])
                if result["generated"]:
                    st.caption("Explained by Gemini · Grounded in recorded project evidence")
                elif not ai.available:
                    st.caption("Recorded project reason · Gemini is not connected")
    with st.expander("Add project context"):
        with st.form("add_memory"):
            category = st.selectbox("Category", ["Goals", "Requirements", "Technology", "Completed", "Pending", "Important Context", "Open Questions", "Risks / Issues"])
            content = st.text_area("Context item")
            source = st.text_input("Source (optional)")
            if st.form_submit_button("Save to memory"):
                if content.strip():
                    db.save_memory(current_id, category, content, source or "user", member_name=st.session_state.member_name)
                    st.rerun()
                else:
                    st.warning("Add some context first.")

elif page == "Tasks":
    page_header("PROJECT WORK", "Tasks", "Track the work that moves this project forward.")
    with st.form("new_task", clear_on_submit=True):
        title_col, assignee_col, action_col = st.columns([3, 2, 1])
        title = title_col.text_input("Task title")
        assignee = assignee_col.text_input("Assignee (optional)")
        add_task = action_col.form_submit_button("Add task", type="primary", use_container_width=True)
    if add_task:
        if title.strip():
            db.save_task(current_id, title, assignee=assignee, member_name=st.session_state.member_name)
            st.rerun()
        else:
            st.warning("Enter a task title.")
    tasks = db.get_rows("tasks", current_id)
    if not tasks:
        st.info("No tasks yet. Tasks will appear here as they’re added or extracted from project material.")
    for task in tasks:
        with st.container(border=True):
            task_col, status_col = st.columns([4, 1.5])
            task_col.markdown(f"**{task['title']}**")
            author = task.get("member_name") or task.get("created_by") or "Project member"
            task_col.caption(f"{task['assignee'] or 'Unassigned'} · Created by {author} · {task['source'] or 'User-added'}")
            statuses = ["Pending", "In Progress", "Completed"]
            selected = status_col.selectbox("Status", statuses, index=statuses.index(task["status"]) if task["status"] in statuses else 0, key=f"status_{task['id']}", label_visibility="collapsed")
            if selected != task["status"]:
                db.update_task(task["id"], selected, current_id, st.session_state.member_name)
                st.rerun()

elif page == "Activity":
    page_header("PROJECT HISTORY", "Activity", "A timeline of project files, decisions, tasks, and conversations.")
    events = db.get_rows("activity", current_id, 100)
    if not events:
        st.info("No activity yet. Project changes will appear here.")
    for event in events:
        with st.container(border=True):
            st.markdown(f"**{event['event_type'].replace('_', ' ').title()}** · {event['description']}")
            st.caption(event["created_at"][:16].replace("T", " "))
