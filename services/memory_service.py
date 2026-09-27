from .project_service import get_rows, save_memory, save_decision, save_task

CATEGORIES={"goals":"Goals","requirements":"Requirements","technologies":"Important Context","completed":"Completed","pending":"Pending","important_context":"Important Context","open_questions":"Open Questions","risks":"Risks / Issues"}


def store_extraction(pid,data,source=""):
    if not isinstance(data,dict): raise ValueError("AI extraction was not a JSON object")
    count=0
    for key,category in CATEGORIES.items():
        values=data.get(key,[])
        if not isinstance(values,list): continue
        for item in values:
            content=item.get("content",item.get("title","")) if isinstance(item,dict) else str(item)
            if content:
                save_memory(pid,category,content,source); count+=1
    for decision in data.get("decisions",[]) if isinstance(data.get("decisions",[]),list) else []:
        if isinstance(decision,dict) and decision.get("title"):
            save_decision(pid,decision["title"],decision.get("description",""),decision.get("reason",""),decision.get("source") or source); count+=1
    for task in data.get("tasks",[]) if isinstance(data.get("tasks",[]),list) else []:
        if isinstance(task,dict) and task.get("title"):
            save_task(pid,task["title"],task.get("status","Pending"),task.get("assignee","") or "",task.get("source") or source); count+=1
    for value in data.get("pending",[]) if isinstance(data.get("pending",[]),list) else []:
        title=value.get("title","") if isinstance(value,dict) else str(value)
        if title: save_task(pid,title,"Pending","",source)
    return count


def build_context(project,pid):
    from .project_service import get_rows
    parts=[f"Project: {project['name']}\nDescription: {project['description']}"]
    for label,table in [("PROJECT MEMORY","memory_items"),("DECISIONS","decisions"),("TASKS","tasks"),("RECENT ACTIVITY","activity"),("UPLOADED FILES","files"),("RECENT CONVERSATION","messages")]:
        rows=get_rows(table,pid,40)
        if not rows: continue
        parts.append(f"\n{label}")
        for row in reversed(rows):
            if table=="memory_items": parts.append(f"[{row['category']}] {row['content']} (source: {row['source'] or 'not recorded'})")
            elif table=="decisions": parts.append(f"{row['title']}: {row['description']} Reason: {row['reason'] or 'not recorded'}. Source: {row['source'] or 'not recorded'}")
            elif table=="tasks": parts.append(f"{row['status']}: {row['title']} (assignee: {row['assignee'] or 'unassigned'})")
            elif table=="activity": parts.append(f"{row['created_at']}: {row['description']}")
            elif table=="files": parts.append(f"{row['filename']}: {(row['extracted_text'] or '[no text extracted]')[:3000]}")
            else: parts.append(f"{row['role']}: {row['content']}")
    return "\n".join(parts)
