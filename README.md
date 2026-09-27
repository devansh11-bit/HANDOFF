# HANDOFF

**One project. One shared context.** HANDOFF turns project files and conversations into persistent, source-aware memory so teammates can return to work without starting from zero.

## Features

- Create persistent project workspaces with SQLite.
- Upload PNG/JPG images, PDFs, text, and Markdown for Gemini analysis.
- Keep extracted goals, requirements, decisions, completed work, tasks, open questions, and risks in project memory.
- Ask project-grounded questions, record decisions, and manage tasks.
- Generate Catch Me Up summaries and downloadable Markdown handoff packages.
- Browse project activity and the product specifications in the app.
- Create a Smart Waste Management demo workspace.

## Run locally

1. Install Python 3.10+ and create/activate a virtual environment.
2. Install packages: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`, then add your Gemini API key and an available model name:

   ```text
   GEMINI_API_KEY=your_key_here
   GEMINI_MODEL=your_available_model
   ```

4. Start the app: `streamlit run app.py`

Without Gemini credentials, project management, memory, tasks, and the demo still work; AI actions show a clear setup message and handoff can use the recorded memory fallback.

## Shared projects

By default, HANDOFF uses SQLite and local files. The sidebar shows that this is local development mode; project codes work only against the same local installation. To enable cross-device collaboration, configure SUPABASE_URL and SUPABASE_KEY, run supabase_setup/schema.sql in the Supabase SQL Editor, and create the private project-files bucket (the schema creates it). Set SUPABASE_SERVICE_ROLE_KEY only as a server-side deployment secret when private Storage policies require it; it takes precedence over SUPABASE_KEY and must never be exposed to a browser or committed. Set HANDOFF_BASE_URL to the deployed app URL to produce invite links.

Members can create a project, share its code or invite link, and join by entering a display name. Projects share files, memory, decisions, tasks, chat, and activity. The MVP uses project codes and names without sign-in; do not use it for sensitive data until stronger member authentication and access policies are added.

## Architecture

Streamlit provides the workspace UI. Python service modules handle SQLite persistence, local file processing, memory normalization, Gemini calls, and handoff generation. Uploaded files live under `data/projects/<project_id>/files/`; SQLite stores project metadata and extracted text. Set `GEMINI_API_KEY` and `GEMINI_MODEL` as Streamlit Community Cloud secrets for hosted use. Do not commit `.env` or private project files.

## Demo flow

Create the Smart Waste demo, review its ESP32 decision and pending tasks, ask “Why did we choose ESP32?”, try Catch Me Up, and download a Handoff Package. Upload a project document or image to see Gemini extract new memory.

## Project structure

```text
app.py
services/       SQLite, files, Gemini, memory, handoff
prompts/        Centralized Gemini prompts
data/           Local database and ignored project uploads
HANDOFF_PRD.md
HANDOFF_DESIGN.md
HANDOFF_TECH_STACK.md
```

## Documentation

- [HANDOFF_PRD.md](HANDOFF_PRD.md) — what HANDOFF should do
- [HANDOFF_DESIGN.md](HANDOFF_DESIGN.md) — how HANDOFF is structured
- [HANDOFF_TECH_STACK.md](HANDOFF_TECH_STACK.md) — what technologies HANDOFF uses

These specification documents are also available in the app sidebar under **Project Documentation**.
