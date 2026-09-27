# HANDOFF --- Design & Architecture Document

## 1. Design Objective

Build a lightweight collaborative project workspace where Gemini
converts scattered project information into persistent, structured
context.

The architecture should be: - simple enough for a solo hackathon build -
easy to debug - inexpensive - modular enough to extend later

------------------------------------------------------------------------

## 2. High-Level Architecture

``` text
                    ┌─────────────────────┐
                    │      USER           │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   STREAMLIT UI      │
                    │                     │
                    │ Overview            │
                    │ Files               │
                    │ Project Chat        │
                    │ Memory              │
                    │ Tasks               │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ APPLICATION LAYER   │
                    │                     │
                    │ Project Manager     │
                    │ File Processor      │
                    │ AI Service          │
                    │ Memory Manager      │
                    │ Handoff Generator   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │ Project DB   │ │ File Storage │ │ Gemini API   │
      │              │ │              │ │              │
      │ projects     │ │ PDFs/images  │ │ multimodal   │
      │ messages     │ │ notes        │ │ reasoning    │
      │ memory       │ │              │ │ extraction   │
      │ tasks        │ │              │ │ generation   │
      └──────────────┘ └──────────────┘ └──────────────┘
```

------------------------------------------------------------------------

## 3. Recommended MVP Architecture

For the hackathon, keep the architecture intentionally small:

``` text
Streamlit
   │
   ├── Python application logic
   │
   ├── SQLite
   │
   ├── Local uploads
   │
   └── Gemini API
```

Do not introduce a separate frontend/backend service unless necessary.

------------------------------------------------------------------------

## 4. Application Modules

### 4.1 Project Manager

Responsibilities: - create project - load project - update project
metadata - maintain current project state

Example object:

``` text
Project
├── id
├── name
├── description
├── created_at
└── updated_at
```

------------------------------------------------------------------------

### 4.2 File Processor

Responsibilities: - accept uploads - identify file type - extract text
where appropriate - preserve images/PDFs for multimodal analysis -
associate files with a project

Supported MVP inputs: - PNG/JPG - PDF - TXT/Markdown

------------------------------------------------------------------------

### 4.3 Gemini Service

All Gemini API calls should live behind one service layer.

Example conceptual interface:

``` python
analyze_project_material(...)
ask_project_question(...)
extract_memory(...)
generate_catchup(...)
generate_handoff(...)
```

This keeps AI logic out of the UI code.

------------------------------------------------------------------------

## 5. Project Memory Model

The most important architectural concept is **structured memory**.

A project should maintain:

``` text
Project Memory
│
├── Goals
├── Requirements
├── Decisions
├── Completed
├── Pending
├── Tasks
├── Important Context
├── Open Questions
└── Risks / Issues
```

### Decision example

``` json
{
  "title": "Use ESP32",
  "reason": "Wi-Fi capability and project budget",
  "source": "meeting_notes.pdf",
  "created_at": "..."
}
```

### Task example

``` json
{
  "title": "Calibrate ultrasonic sensor",
  "status": "pending",
  "assignee": "unassigned",
  "source": "project_chat",
  "created_at": "..."
}
```

------------------------------------------------------------------------

## 6. Data Model

### projects

``` text
id
name
description
created_at
updated_at
```

### files

``` text
id
project_id
filename
file_type
path
uploaded_at
```

### messages

``` text
id
project_id
role
content
created_at
```

### decisions

``` text
id
project_id
title
description
reason
source
created_at
```

### tasks

``` text
id
project_id
title
status
assignee
source
created_at
```

### memory_items

``` text
id
project_id
category
content
source
confidence
created_at
```

For the MVP, these can be implemented as SQLite tables.

------------------------------------------------------------------------

## 7. AI Context Pipeline

### Step 1 --- Ingest

User uploads material.

``` text
File
 ↓
File Processor
 ↓
Text / image / PDF content
```

### Step 2 --- Analyze

Relevant content is sent to Gemini.

``` text
Project Material
       ↓
     Gemini
       ↓
Structured extraction
```

### Step 3 --- Normalize

The application converts the response into a predictable structure.

``` text
{
  goals: [],
  requirements: [],
  decisions: [],
  tasks: [],
  completed: [],
  pending: [],
  important_context: [],
  open_questions: []
}
```

### Step 4 --- Store

Store extracted memory in SQLite.

### Step 5 --- Retrieve

When the user asks a question, retrieve the relevant project context.

### Step 6 --- Generate

Send: - project context - relevant files/content - recent messages -
user question

to Gemini.

------------------------------------------------------------------------

## 8. Project Chat Architecture

The chat should not send the entire database on every request.

For the MVP:

1.  Load project memory.
2.  Load recent messages.
3.  Identify relevant project material.
4.  Build a compact context block.
5.  Send the context + question to Gemini.
6.  Store the response.

Conceptually:

``` text
User Question
     │
     ▼
Project Context
     │
     ├── Memory
     ├── Recent Chat
     └── Relevant Files
     │
     ▼
Gemini
     │
     ▼
Grounded Answer
```

------------------------------------------------------------------------

## 9. Catch Me Up Architecture

Input:

-   project memory
-   recent activity
-   previous snapshot/reference point
-   new files
-   new decisions
-   completed tasks

Gemini generates:

``` text
Catch Me Up
├── What changed
├── New decisions
├── Completed
├── Pending
├── Important issues
└── Recommended next actions
```

Important rule:

**Do not fabricate changes.**

If no evidence exists, say so.

------------------------------------------------------------------------

## 10. Handoff Package Architecture

The package should be generated from structured project memory plus
relevant history.

Output:

``` text
HANDOFF PACKAGE

1. Project Overview
2. Current State
3. Completed Work
4. Pending Work
5. Important Decisions
6. Why Those Decisions Were Made
7. Known Issues
8. Open Questions
9. Next Actions
10. Important Files / Sources
```

------------------------------------------------------------------------

## 11. UI Structure

### Page 1 --- Project Home

``` text
┌─────────────────────────────────────────┐
│ HANDOFF                    Project Name │
├─────────────────────────────────────────┤
│                                         │
│ Project status: 62%                     │
│                                         │
│ [ Catch Me Up ] [ Generate Handoff ]    │
│                                         │
│ Recent Changes                          │
│ • Backend changed to Firebase           │
│ • Sensor testing completed              │
│                                         │
│ Pending Tasks                           │
│ □ Dashboard                             │
│ □ Final testing                         │
│                                         │
│ Recent Decisions                        │
│ • ESP32 selected                        │
└─────────────────────────────────────────┘
```

### Page 2 --- Files

Upload/drop files and show: - filename - type - upload date - processing
status

### Page 3 --- Project Chat

Chat interface with: - user messages - AI answers - source/context
indicators - "Save as decision" - "Create task"

### Page 4 --- Memory

Tabs/cards: - Decisions - Tasks - Completed - Pending - Important
Context - Open Questions

### Page 5 --- Activity

Timeline:

``` text
Today
│
├── Firebase decision added
├── Requirements.pdf uploaded
└── Sensor task completed
```

------------------------------------------------------------------------

## 12. AI Prompt Strategy

Use structured prompts rather than open-ended prompts.

Example extraction instruction:

``` text
You are the project-context engine for HANDOFF.

Analyze the supplied project material.

Extract only information supported by the material.

Return structured JSON with:
- goals
- requirements
- decisions
- completed
- pending
- tasks
- important_context
- open_questions
- risks

Do not invent missing information.
If something is unknown, leave it empty.
For each item, include a source when possible.
```

For project chat:

``` text
You are HANDOFF's project assistant.

Answer using the supplied project context.

Rules:
1. Prefer project evidence over generic knowledge.
2. Do not invent project decisions.
3. If the answer is not present in project context, say that it is not recorded.
4. Distinguish project facts from suggestions.
5. Keep answers concise and actionable.
```

------------------------------------------------------------------------

## 13. Security & Privacy Design

For the hackathon MVP: - API key stored in `.env` - `.env` excluded from
Git - uploaded files associated with a project - do not expose API keys
in frontend code - avoid logging sensitive file contents - show users
that AI-generated information should be verified

------------------------------------------------------------------------

## 14. Failure Handling

### Gemini unavailable

Show:

> "AI service temporarily unavailable. Your project data is still
> available."

### Unsupported file

Show:

> "This file type is not supported in the MVP."

### No context

Show:

> "I couldn't find this information in the project context."

### AI uncertainty

Use:

> "Not recorded in the project."

rather than inventing an answer.

------------------------------------------------------------------------

## 15. MVP vs Future Architecture

### MVP

``` text
Streamlit
SQLite
Local file storage
Gemini API
```

### Future

``` text
React / Next.js
FastAPI
PostgreSQL
Object storage
Vector database
Gemini API
Authentication
Real-time collaboration
Integrations
```

The MVP architecture should remain simple enough to finish during the
hackathon.

------------------------------------------------------------------------

## 16. Demo Architecture

For the hackathon demo, use one realistic project.

Recommended example:

**Smart Waste Management System**

Inputs: - problem statement PDF - component image - meeting notes -
requirements

Demo:

``` text
Upload
  ↓
AI extraction
  ↓
Project Memory
  ↓
Project Chat
  ↓
Decision update
  ↓
Catch Me Up
  ↓
Handoff Package
```

------------------------------------------------------------------------

## 17. Key Architectural Principle

HANDOFF is not primarily a chatbot.

The system of record is:

> **Project Memory**

The chatbot is one interface for interacting with that memory.

That distinction should remain central to the architecture.
