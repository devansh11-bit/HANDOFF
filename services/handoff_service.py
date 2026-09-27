from .project_service import get_rows


def fallback_handoff(project, pid):
    decisions = get_rows("decisions", pid)
    tasks = get_rows("tasks", pid)
    memory = get_rows("memory_items", pid)
    files = get_rows("files", pid)

    def lines(rows, formatter):
        return "\n".join("- " + formatter(row) for row in rows) or "- Not recorded in current project context."

    completed = [task for task in tasks if task["status"] == "Completed"]
    pending = [task for task in tasks if task["status"] != "Completed"]
    return f"""# Project Handoff: {project['name']}

## Project Overview
{project['description'] or 'Not recorded.'}

## Current State
Project memory contains {len(memory)} items, {len(decisions)} decisions, and {len(tasks)} tasks.

## Completed Work
{lines(completed, lambda row: row['title'])}

## Pending Work
{lines(pending, lambda row: row['title'] + ' (' + row['status'] + ')')}

## Important Decisions
{lines(decisions, lambda row: row['title'] + ' — ' + (row['description'] or 'No description'))}

## Why Those Decisions Were Made
{lines([row for row in decisions if row['reason']], lambda row: row['title'] + ': ' + row['reason'])}

## Known Issues
{lines([row for row in memory if row['category'] == 'Risks / Issues'], lambda row: row['content'])}

## Open Questions
{lines([row for row in memory if row['category'] == 'Open Questions'], lambda row: row['content'])}

## Next Actions
{lines(pending, lambda row: row['title'])}

## Important Files / Sources
{lines(files, lambda row: row['filename'])}
"""
