# HANDOFF --- Technical Stack Specification

## 1. Technical Goal

Use the simplest reliable technology stack that can produce a convincing
working MVP during the hackathon.

The stack should prioritize: - speed of development - Gemini
integration - easy local development - easy deployment - minimal
infrastructure - maintainability

------------------------------------------------------------------------

## 2. Recommended Stack

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  UI                      Streamlit               Fast interactive web
                                                  interface

  Language                Python 3                Main application
                                                  language

  AI SDK                  `google-genai`          Gemini API integration

  AI Model                Gemini Flash model      Multimodal
                          available in the        understanding +
                          current API account     reasoning

  Environment             `python-dotenv`         Load API key from
                                                  `.env`

  Image handling          Pillow                  Image processing

  Database                SQLite                  Project memory and
                                                  metadata

  File storage            Local filesystem for    Uploaded files
                          MVP                     

  Version control         Git + GitHub            Source
                                                  control/submission

  Deployment              Streamlit-compatible    Public demo
                          hosting                 

  Editor                  VS Code                 Development
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 3. Python Packages

Initial requirements:

``` text
streamlit
google-genai
python-dotenv
pillow
```

For later expansion, optional packages may include:

``` text
pypdf
```

for PDF text extraction if required by the chosen ingestion approach.

Keep dependencies minimal during the hackathon.

------------------------------------------------------------------------

## 4. Project Structure

Recommended structure:

``` text
handoff-ai/
│
├── app.py
├── requirements.txt
├── .env
├── .gitignore
│
├── services/
│   ├── gemini_service.py
│   ├── project_service.py
│   └── memory_service.py
│
├── data/
│   └── projects/
│
├── prompts/
│   ├── extraction.txt
│   ├── chat.txt
│   ├── catchup.txt
│   └── handoff.txt
│
└── README.md
```

For the first prototype, it is acceptable to keep everything in
`app.py`. Refactor into modules after the core workflow works.

------------------------------------------------------------------------

## 5. Gemini Integration

Use Google's current Python SDK:

``` python
from google import genai

client = genai.Client(api_key=API_KEY)
```

Then call the current Gemini Flash model available to the account.

Example pattern:

``` python
response = client.models.generate_content(
    model="MODEL_NAME",
    contents="Your prompt"
)
```

Keep the model name configurable so it can be changed without rewriting
application logic.

------------------------------------------------------------------------

## 6. Environment Variables

`.env`:

``` text
GEMINI_API_KEY=your_key_here
```

Never commit `.env`.

`.gitignore`:

``` text
venv/
.env
__pycache__/
*.pyc
data/projects/
```

If project demo data is safe to publish, a sanitized sample dataset can
be stored separately.

------------------------------------------------------------------------

## 7. Database

Use SQLite for the MVP.

### Why SQLite?

-   zero setup
-   local file database
-   built into Python
-   easy to inspect
-   sufficient for a single-user/small-team demo
-   avoids wasting hackathon time on infrastructure

### Tables

``` text
projects
files
messages
memory_items
decisions
tasks
activity
```

------------------------------------------------------------------------

## 8. File Storage

For MVP:

``` text
data/
└── projects/
    └── <project_id>/
        ├── files/
        └── extracted/
```

Store: - original uploaded file - extracted text/metadata where
applicable

Do not store API keys in this directory.

------------------------------------------------------------------------

## 9. AI Data Flow

``` text
                 UPLOAD
                    │
                    ▼
             File Processor
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       Text/PDF              Image
          │                   │
          └─────────┬─────────┘
                    ▼
                  Gemini
                    │
                    ▼
           Structured JSON
                    │
                    ▼
             SQLite Memory
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     Chat        Catch Up      Handoff
```

------------------------------------------------------------------------

## 10. Structured AI Output

Gemini should produce predictable JSON wherever possible.

Example:

``` json
{
  "goals": [],
  "requirements": [],
  "decisions": [
    {
      "title": "Use ESP32",
      "reason": "Wi-Fi support and budget",
      "source": "meeting_notes.pdf"
    }
  ],
  "completed": [],
  "pending": [],
  "tasks": [],
  "important_context": [],
  "open_questions": [],
  "risks": []
}
```

The application should validate the returned structure before saving it.

------------------------------------------------------------------------

## 11. Chat Context Strategy

For the hackathon:

### Context sent to Gemini

``` text
Project description
+
Project memory
+
Relevant uploaded material
+
Recent conversation
+
Current user question
```

Avoid sending every file and every message on every request.

This keeps prompts smaller and responses faster.

------------------------------------------------------------------------

## 12. Retrieval Strategy

### MVP

Use: - project memory - recent messages - simple filename/type
filtering - extracted text

### Later

Introduce semantic retrieval:

``` text
Documents
    ↓
Embeddings
    ↓
Vector database
    ↓
Relevant chunks
    ↓
Gemini
```

Possible future technologies: - pgvector - Chroma - FAISS

Do not add this complexity during the initial hackathon build unless
required.

------------------------------------------------------------------------

## 13. Collaboration Strategy

The hackathon MVP can simulate collaboration using a shared project
workspace.

Minimum model:

``` text
Project
  ├── shared files
  ├── shared memory
  ├── shared chat
  └── shared tasks
```

A true multi-user account system is a future feature.

If time permits, add a simple display name field so messages can show:

``` text
Aarav:
Let's use Firebase.

Rahul:
Agreed.
```

------------------------------------------------------------------------

## 14. Catch Me Up Implementation

Store activity events:

``` text
FILE_UPLOADED
DECISION_ADDED
TASK_COMPLETED
TASK_CREATED
MESSAGE_ADDED
MEMORY_UPDATED
```

Catch Me Up uses the relevant activity range.

Example:

``` text
Previous checkpoint
        ↓
New activity
        ↓
Gemini
        ↓
Catch Me Up
```

------------------------------------------------------------------------

## 15. Handoff Package Implementation

Generate Markdown first.

Example:

``` markdown
# Project Handoff

## Current State

...

## Completed

- ...

## Pending

- ...

## Important Decisions

- ...

## Known Issues

- ...

## Next Actions

1. ...
2. ...
```

This can later be exported to PDF.

------------------------------------------------------------------------

## 16. Deployment

Recommended hackathon deployment:

### Streamlit Community Cloud

Advantages: - simple deployment - Python-native - GitHub integration -
suitable for a Streamlit MVP

Set the Gemini API key as a deployment secret/environment variable
rather than committing `.env`.

Alternative deployment platforms can be used if Streamlit hosting is
unavailable.

------------------------------------------------------------------------

## 17. Git Workflow

Initial repository:

``` bash
git init
git add .
git commit -m "Initial HANDOFF MVP"
```

Then create a GitHub repository and push the project.

Do not commit:

``` text
.env
venv/
private project files
API keys
```

------------------------------------------------------------------------

## 18. Performance Considerations

For the hackathon: - keep uploaded files reasonably small - process
files only when needed - cache project-level information where
practical - avoid repeatedly sending identical content to Gemini - use
concise prompts - store extracted project memory locally

------------------------------------------------------------------------

## 19. Security

Minimum requirements:

1.  Never expose the Gemini API key in frontend code.
2.  Never commit `.env`.
3.  Do not log API keys.
4.  Do not display raw secrets in errors.
5.  Treat uploaded project material as private.
6.  Do not claim AI-generated project facts are guaranteed correct.
7.  Preserve source references where practical.

------------------------------------------------------------------------

## 20. Testing Checklist

### Gemini

-   [ ] API key loads
-   [ ] Basic generation works
-   [ ] Image input works
-   [ ] PDF/document workflow works
-   [ ] Structured output parses

### Project

-   [ ] Create project
-   [ ] Upload file
-   [ ] Project memory updates
-   [ ] Ask project question
-   [ ] Save decision
-   [ ] Create task
-   [ ] Catch Me Up works
-   [ ] Handoff Package works

### Security

-   [ ] `.env` ignored
-   [ ] API key not in Git history
-   [ ] secrets configured in deployment

### Demo

-   [ ] Demo project prepared
-   [ ] Sample files ready
-   [ ] No broken buttons
-   [ ] Public deployment works
-   [ ] README explains Gemini usage

------------------------------------------------------------------------

## 21. Hackathon Priority Order

If time becomes limited, implement in this order:

### P0 --- Must work

1.  Gemini connection
2.  Project creation
3.  File upload
4.  Gemini project analysis
5.  Project memory
6.  Project chat

### P1 --- Strong demo features

7.  Catch Me Up
8.  Decision capture
9.  Task extraction
10. Handoff Package

### P2 --- Only if time remains

11. Activity timeline
12. Source citations
13. Multiple project members
14. Export
15. Advanced retrieval

------------------------------------------------------------------------

## 22. Final Technical Principle

Do not over-engineer.

The hackathon version should prove one technical idea:

> **Gemini can transform scattered project information into a
> persistent, useful project context that another person can immediately
> understand and act on.**

Everything else is secondary.
