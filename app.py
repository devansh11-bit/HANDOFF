import streamlit as st
from pathlib import Path
from services import project_service as db
from services.file_service import save_upload
from services.gemini_service import GeminiService
from services.memory_service import store_extraction, build_context
from services.handoff_service import fallback_handoff

st.set_page_config(page_title="HANDOFF", page_icon="↗", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif} h1,h2,h3{font-family:'Manrope',sans-serif}
[data-testid="stAppViewContainer"]{background:#f6f7f9} [data-testid="stSidebar"]{background:#111c28;color:#eef3f7}
[data-testid="stSidebar"] *{color:#eef3f7} .hero{padding:1.5rem 1.8rem;border-radius:18px;background:linear-gradient(115deg,#142536,#244f51);color:white;margin-bottom:1.2rem}
.stApp [data-testid="stMarkdownContainer"],.stApp label{color:#18232f}.hero,.hero *{color:white}.hero h1{margin:0;font-size:2.4rem}.hero p{color:#d6e5e5;margin:.5rem 0 0}.hero .eyebrow{letter-spacing:.12em;text-transform:uppercase;font-size:.74rem;color:#adcac4;font-weight:700}
div[data-testid="stMetric"]{background:white;padding:1rem;border:1px solid #e7eaee;border-radius:14px} .block-container{padding-top:2rem}
</style>""", unsafe_allow_html=True)

db.init_db()
ai=GeminiService()

def event_context(pid):
    project=db.get_project(pid)
    return build_context(project,pid)

def show_memory(rows):
    if not rows: st.caption("No project memory recorded yet."); return
    for row in rows:
        st.markdown(f"**{row['category']}** · {row['content']}")
        if row.get('source'): st.caption(f"Source: {row['source']}")

st.sidebar.markdown("# ↗ HANDOFF")
st.sidebar.caption("One project. One shared context.")
projects=db.get_projects()
if projects:
    labels={f"{p['name']}":p['id'] for p in projects}
    current_id=st.sidebar.selectbox("Your projects",options=list(labels.values()),format_func=lambda pid:next(p['name'] for p in projects if p['id']==pid),key="project_select")
    project=db.get_project(current_id)
    page=st.sidebar.radio("WORKSPACE",["Overview","Files","Project Chat","Memory","Tasks","Activity"])
else:
    current_id=None; project=None; page="Overview"
    st.sidebar.info("Create a project to begin.")
with st.sidebar.expander("Project Documentation"):
    st.caption("📋 Product Requirements")
    st.markdown((Path(__file__).parent/"HANDOFF_PRD.md").read_text(encoding="utf-8"))
    st.caption("🏗️ Design & Architecture")
    st.markdown((Path(__file__).parent/"HANDOFF_DESIGN.md").read_text(encoding="utf-8"))
    st.caption("💻 Technical Stack")
    st.markdown((Path(__file__).parent/"HANDOFF_TECH_STACK.md").read_text(encoding="utf-8"))
if not ai.available:
    st.sidebar.warning("Gemini is not configured. Add GEMINI_API_KEY and GEMINI_MODEL in .env to enable AI features.")

st.markdown('<div class="hero"><div class="eyebrow">PROJECT CONTINUITY WORKSPACE</div><h1>HANDOFF</h1><p>Chatbots answer questions. HANDOFF remembers the project.</p></div>',unsafe_allow_html=True)

if not projects:
    left,right=st.columns([1.1,1])
    with left:
        st.subheader("Start a shared project context")
        with st.form("new_project"):
            name=st.text_input("Project name",placeholder="Smart Waste Management System")
            desc=st.text_area("Project description",placeholder="What are you building, and what should teammates know?")
            create=st.form_submit_button("Create project",type="primary",use_container_width=True)
        if create:
            if not name.strip(): st.error("Enter a project name.")
            else:
                pid=db.create_project(name,desc); st.session_state.project_select=pid; st.rerun()
    with right:
        st.subheader("Try the demo workspace")
        st.write("Explore a realistic project with recorded decisions, tasks, and context.")
        if st.button("Create Smart Waste demo",type="primary"):
            pid=db.create_project("Smart Waste Management System","Build a smart waste-bin monitoring prototype that measures bin fill level and helps teams plan collection.")
            db.save_memory(pid,"Goals","Monitor waste-bin fill level using an ESP32-based prototype.","Demo project brief")
            db.save_memory(pid,"Important Context","Ultrasonic distance sensor measures the remaining space in the bin.","Demo component list")
            db.save_memory(pid,"Completed","Initial hardware research completed.","Demo project brief")
            db.save_memory(pid,"Pending","Prototype assembly, backend integration, and testing remain.","Demo project brief")
            db.save_decision(pid,"Use ESP32 for the prototype","Selected as the prototype controller.","It provides Wi-Fi connectivity and sufficient GPIO for the prototype.","Demo requirements meeting")
            db.save_task(pid,"Assemble the sensor prototype",source="Demo project brief")
            db.save_task(pid,"Integrate the backend",source="Demo project brief")
            db.save_task(pid,"Test fill-level readings",source="Demo project brief")
            st.session_state.project_select=pid; st.rerun()
    st.stop()

context=event_context(current_id)
if page=="Overview":
    st.subheader(project["name"])
    st.write(project["description"] or "No project description added yet.")
    tasks=db.get_rows("tasks",current_id); decisions=db.get_rows("decisions",current_id); files=db.get_rows("files",current_id); memory=db.get_rows("memory_items",current_id)
    done=sum(t['status']=="Completed" for t in tasks); pct=int(done/len(tasks)*100) if tasks else 0
    c1,c2,c3,c4=st.columns(4); c1.metric("Progress",f"{pct}%"); c2.metric("Open tasks",sum(t['status']!="Completed" for t in tasks)); c3.metric("Decisions",len(decisions)); c4.metric("Project files",len(files))
    a,b,c=st.columns(3)
    if a.button("⚡ Catch Me Up",use_container_width=True,type="primary"):
        try: st.session_state.catchup=ai.generate_catchup(context)
        except Exception as exc: st.session_state.catchup=f"AI unavailable: {exc}"
    if b.button("📦 Generate Handoff",use_container_width=True):
        try: st.session_state.handoff=ai.generate_handoff(context)
        except Exception: st.session_state.handoff=fallback_handoff(project,current_id)
    if c.button("💬 Go to Project Chat",use_container_width=True): st.session_state.workspace_page="Project Chat"
    if "catchup" in st.session_state:
        st.markdown("### Your catch-up"); st.markdown(st.session_state.catchup)
    if "handoff" in st.session_state:
        st.markdown("### Handoff package"); st.markdown(st.session_state.handoff)
        st.download_button("Download handoff (.md)",st.session_state.handoff,file_name="project-handoff.md",mime="text/markdown")
    x,y=st.columns(2)
    with x:
        st.markdown("### Pending work")
        pending=[t for t in tasks if t['status']!="Completed"]
        for task in pending[:6]: st.markdown(f"- **{task['title']}** · {task['status']}")
        if not pending: st.caption("No pending tasks recorded.")
    with y:
        st.markdown("### Recent decisions")
        for decision in decisions[:5]: st.markdown(f"- **{decision['title']}** — {decision['reason'] or 'Reason not recorded'}")
        if not decisions: st.caption("No decisions recorded yet.")
    st.markdown("### Project memory")
    show_memory(memory[:8])
    st.markdown("### Recent activity")
    for e in db.get_rows("activity",current_id,5): st.caption(f"{e['created_at'][:16].replace('T',' ')} · {e['description']}")
elif page=="Files":
    st.subheader("Project files")
    uploads=st.file_uploader("Add project material",type=["png","jpg","jpeg","pdf","txt","md"],accept_multiple_files=True)
    if uploads:
        for uploaded in uploads:
            if st.button(f"Process {uploaded.name}",key=f"upload_{uploaded.name}"):
                try:
                    path,text=save_upload(current_id,uploaded)
                    db.add_file(current_id,uploaded.name,path.suffix.lower().lstrip('.'),str(path),text)
                    if ai.available:
                        with st.spinner(f"Gemini is understanding {uploaded.name}…"):
                            extracted=ai.analyze_project_material(uploaded.name,text,str(path))
                            count=store_extraction(current_id,extracted,uploaded.name)
                        st.success(f"Uploaded and added {count} memory items from {uploaded.name}.")
                    else: st.success(f"Uploaded {uploaded.name}. Configure Gemini to extract project memory.")
                    st.rerun()
                except Exception as exc: st.error(f"Could not process this file: {exc}")
    files=db.get_rows("files",current_id)
    if files:
        for f in files: st.markdown(f"📄 **{f['filename']}** · {f['file_type'].upper()} · {f['uploaded_at'][:10]}")
    else: st.info("Project files will appear here after upload.")
elif page=="Project Chat":
    st.subheader("Project Chat"); st.caption("Answers use recorded memory, uploaded material, and recent project conversation.")
    for message in reversed(db.get_rows("messages",current_id,80)):
        with st.chat_message(message['role']): st.markdown(message['content'])
    question=st.chat_input("Ask about this project…")
    if question:
        db.save_message(current_id,"user",question)
        try: answer=ai.ask_project_question(question,build_context(project,current_id))
        except Exception as exc: answer=f"I can't reach Gemini right now: {exc}"
        db.save_message(current_id,"assistant",answer); st.rerun()
    with st.expander("Save a decision or create a task"):
        dtab,ttab=st.tabs(["Decision","Task"])
        with dtab:
            latest_user=next((m["content"] for m in db.get_rows("messages",current_id,40) if m["role"]=="user"),"")
            with st.form("decision_form"):
                title=st.text_input("Decision",value=latest_user[:160]) ; why=st.text_area("Recorded reason (optional)"); detail=st.text_input("Description (optional)")
                if st.form_submit_button("Save decision"):
                    if title.strip(): db.save_decision(current_id,title,detail,why); st.success("Decision added to project memory.")
                    else: st.warning("Enter a decision title.")
        with ttab:
            with st.form("task_form"):
                task_title=st.text_input("Task"); assignee=st.text_input("Assignee (optional)")
                if st.form_submit_button("Create task"):
                    if task_title.strip(): db.save_task(current_id,task_title,assignee=assignee); st.success("Task created.")
                    else: st.warning("Enter a task title.")
elif page=="Memory":
    st.subheader("Project Memory")
    for category in ["Goals","Requirements","Decisions","Completed","Pending","Important Context","Open Questions","Risks / Issues"]:
        subset=[m for m in db.get_rows("memory_items",current_id,200) if m['category']==category]
        with st.expander(f"{category} · {len(subset)}",expanded=bool(subset)):
            show_memory(subset)
    st.markdown("### Decisions")
    decisions=db.get_rows("decisions",current_id)
    if not decisions: st.caption("No decisions recorded.")
    for d in decisions:
        st.markdown(f"**{d['title']}**\n\n{d['description'] or ''}\n\nReason: {d['reason'] or 'The project memory does not contain a recorded reason for this decision.'}\n\nSource: {d['source'] or 'Not recorded'}")
        if st.button(f"❓ Why? · {d['title']}",key=f"why_{d['id']}"):
            evidence=d['reason'] or "The project memory does not contain a recorded reason for this decision. Do not invent one."
            if ai.available:
                try: st.session_state[f"why_result_{d['id']}"]=ai.ask_project_question(f"Why did we make this decision? Decision: {d['title']}. Recorded reason: {evidence}",context)
                except Exception: st.session_state[f"why_result_{d['id']}"]=evidence
            else: st.session_state[f"why_result_{d['id']}"]=evidence
        if f"why_result_{d['id']}" in st.session_state: st.info(st.session_state[f"why_result_{d['id']}"])
    with st.form("add_memory"):
        st.markdown("### Add project context")
        category=st.selectbox("Category",["Goals","Requirements","Completed","Pending","Important Context","Open Questions","Risks / Issues"])
        content=st.text_area("Context item"); source=st.text_input("Source (optional)")
        if st.form_submit_button("Save to memory"):
            if content.strip():
                from services.project_service import save_memory, connect, record
                save_memory(current_id,category,content,source or "user");
                with connect() as connection: record(connection,current_id,"MEMORY_UPDATED",f"Added {category.lower()} context")
                st.success("Saved to project memory."); st.rerun()
            else: st.warning("Add some context first.")
elif page=="Tasks":
    st.subheader("Project tasks")
    with st.form("new_task"):
        title=st.text_input("Task title"); assignee=st.text_input("Assignee (optional)")
        if st.form_submit_button("Add task",type="primary"):
            if title.strip(): db.save_task(current_id,title,assignee=assignee); st.rerun()
    tasks=db.get_rows("tasks",current_id)
    if not tasks: st.info("No tasks recorded yet.")
    for task in tasks:
        col1,col2,col3=st.columns([4,2,1]); col1.markdown(f"**{task['title']}**\n\n{task['assignee'] or 'Unassigned'} · {task['source'] or 'User-added'}")
        status=col2.selectbox("Status",["Pending","In Progress","Completed"],index=["Pending","In Progress","Completed"].index(task['status']) if task['status'] in ["Pending","In Progress","Completed"] else 0,key=f"status_{task['id']}",label_visibility="collapsed")
        if status!=task['status']: db.update_task(task['id'],status,current_id); st.rerun()
        col3.write("✓" if status=="Completed" else "·")
elif page=="Activity":
    st.subheader("Activity")
    events=db.get_rows("activity",current_id,100)
    if not events: st.caption("No activity recorded yet.")
    for event in events: st.markdown(f"**{event['event_type'].replace('_',' ').title()}** · {event['description']}  \n{event['created_at'][:16].replace('T',' ')}")
