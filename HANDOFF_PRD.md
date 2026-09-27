# HANDOFF --- Product Requirements Document (PRD)

## Shared Projects Addendum

HANDOFF supports team workspaces through Supabase. A member can create a project, share its unique six-character project code or invite URL, and invite teammates who join with a display name. The owner is recorded as the first member.

Project files, shared Project Memory, decisions, tasks, activity, and chat belong to the project and are visible to its members. Actions record the member name where applicable. Project Chat, Catch Me Up, and Handoff Package use the shared project context and recorded activity.

Local development remains available through SQLite and local files when Supabase is not configured. In that mode, project codes and data work only on that local installation; cloud collaboration requires SUPABASE_URL and SUPABASE_KEY.

## 1. Product Overview

**Product:** HANDOFF\
**Tagline:** One project. One shared context.

HANDOFF is an AI-powered collaborative project workspace designed to
solve **context loss during collaboration**.

Project information is normally scattered across documents, images,
notes, chat messages, decisions, and individual memory. When someone
joins, leaves, or returns to a project, they often have to reconstruct
the project history manually.

HANDOFF brings those sources into one project workspace and uses the
Gemini API to turn them into structured, persistent project context.

The MVP focuses on five capabilities:

1.  Project workspace creation
2.  Project material upload and AI understanding
3.  Shared project chat grounded in project context
4.  Structured project memory: decisions, tasks, status, important
    context
5.  "Catch Me Up" and "Handoff Package" generation

------------------------------------------------------------------------

## 2. Problem Statement

### Core problem

**Collaborative work loses context.**

Important knowledge becomes distributed across: - PDFs and documents -
screenshots and images - notes - conversations - decisions - task
updates - individual memory

When a teammate returns after several days, joins midway, or takes over
another person's work, they need to spend time figuring out: - What has
happened? - What is already completed? - What is still pending? - What
decisions were made? - Why were those decisions made? - What should I do
next? - What important detail might I miss?

Existing chat and file tools store information, but the project context
is still difficult to reconstruct.

------------------------------------------------------------------------

## 3. Product Vision

HANDOFF should become a **persistent context layer for collaborative
work**.

Instead of merely storing files or conversations, HANDOFF connects them
into a living project memory.

> **Files + Conversations + Decisions + Tasks + History → Shared Project
> Context**

------------------------------------------------------------------------

## 4. Target Users

### Primary users

-   Student project teams
-   Hackathon teams
-   Small software/product teams
-   Research teams
-   Teams working on temporary projects

### Secondary users

-   Employees handing projects to colleagues
-   People returning to projects after absence
-   Volunteers taking over event/project responsibilities
-   Technicians or operators transferring ongoing work

------------------------------------------------------------------------

## 5. User Personas

### Persona A --- Active Builder

A student who is actively working on a project and wants the AI to
understand the current project.

Needs: - Upload project material - Ask questions about the project -
Record decisions - Track tasks

### Persona B --- Returning Teammate

A teammate who was away for several days.

Needs: - Quickly understand what changed - Know current status - Know
their next task - Avoid reading the entire chat history

### Persona C --- Project Handoff Owner

Someone leaving a project or transferring responsibility.

Needs: - Generate a complete handoff package - Preserve important
decisions - Highlight unfinished work and risks

------------------------------------------------------------------------

## 6. Goals

### MVP goals

1.  Allow a user to create a project workspace.
2.  Allow project material to be uploaded.
3.  Use Gemini to understand uploaded material.
4.  Provide a project-grounded AI chat.
5.  Extract and display:
    -   decisions
    -   completed work
    -   pending work
    -   tasks
    -   important context
    -   open questions
6.  Generate a "Catch Me Up" summary.
7.  Generate a structured handoff package.

### Success criteria

A judge should be able to: 1. Create a project. 2. Upload representative
project material. 3. Ask a project-specific question. 4. See AI-derived
project memory. 5. Simulate a teammate returning to the project. 6.
Click "Catch Me Up". 7. Generate a handoff package.

The complete demo should be understandable in under three minutes.

------------------------------------------------------------------------

## 7. Non-Goals for the Hackathon MVP

Do NOT build these unless the core MVP is already stable:

-   Full enterprise authentication
-   Complex permissions/roles
-   Real-time collaborative editing
-   Full Slack/Discord/WhatsApp integrations
-   Production-grade vector database infrastructure
-   Mobile apps
-   Advanced project management
-   Automatic GitHub code analysis
-   Complex notification systems
-   Billing/subscriptions

These may be future extensions.

------------------------------------------------------------------------

## 8. Core User Journey

### Journey 1 --- Start a project

1.  User opens HANDOFF.
2.  Clicks "New Project".
3.  Enters project name and description.
4.  Workspace is created.

### Journey 2 --- Add context

1.  User uploads PDFs/images/text notes.
2.  HANDOFF sends relevant content to Gemini.
3.  Gemini extracts project information.
4.  HANDOFF updates project memory.

### Journey 3 --- Ask the project

User asks:

> "Why did we choose ESP32?"

HANDOFF answers using the project context rather than generic knowledge.

### Journey 4 --- Update project context

User says:

> "We switched from ThingSpeak to Firebase."

HANDOFF identifies this as a potential project decision and offers:

> Save to Project Memory

### Journey 5 --- Return after absence

User clicks:

> "Catch Me Up"

HANDOFF summarizes: - what changed - new decisions - completed tasks -
pending tasks - issues - recommended next action

### Journey 6 --- Transfer ownership

User clicks:

> "Generate Handoff Package"

HANDOFF creates: - current state - completed work - pending work -
important decisions - reasons behind decisions when available - known
issues - next actions - open questions

------------------------------------------------------------------------

## 9. Functional Requirements

### FR-01 --- Project creation

The system shall allow a user to create a project with: - name -
description

### FR-02 --- Project material upload

The system shall accept at minimum: - images - PDF documents - text
notes

### FR-03 --- AI context extraction

The system shall use Gemini to identify relevant: - goals -
requirements - technologies - decisions - tasks - completed items -
pending items - constraints - open questions

### FR-04 --- Project chat

The system shall allow users to ask questions about project material.

The AI response should be grounded in available project context.

### FR-05 --- Project memory

The system shall maintain structured project memory containing: -
Decisions - Tasks - Completed - Pending - Important Context - Open
Questions

### FR-06 --- Decision capture

When the conversation contains a likely project decision, the UI should
allow the user to save it.

### FR-07 --- Catch Me Up

The system shall generate a concise update describing meaningful changes
since the user's selected reference point or since the previous project
snapshot.

### FR-08 --- Why a decision?

The system should explain the reason behind a decision when evidence
exists in the project material or conversation.

If evidence is unavailable, the system must say that the reason is not
recorded rather than inventing one.

### FR-09 --- Handoff Package

The system shall generate a structured handoff document containing: -
Project overview - Current status - Completed work - Pending work -
Important decisions - Known issues - Open questions - Next actions -
Important context

### FR-10 --- Source awareness

AI-generated claims should be traceable to project material or
conversation when practical.

The UI should distinguish: - information found in project context -
AI-generated suggestions - information that is uncertain or missing

------------------------------------------------------------------------

## 10. UX Requirements

The UI should feel like a focused project workspace, not a generic
chatbot.

### Main navigation

-   Overview
-   Files
-   Project Chat
-   Memory
-   Tasks
-   Activity

### Primary dashboard

Show: - project name - progress/status - latest changes - pending
tasks - recent decisions - "Catch Me Up" - "Generate Handoff"

### Design principles

-   Minimal
-   Fast
-   Clear hierarchy
-   Context-first
-   Avoid excessive AI decoration
-   Make project state visible without opening the chat

------------------------------------------------------------------------

## 11. AI Requirements

Gemini should be used for:

1.  Multimodal project-material understanding
2.  Context extraction
3.  Project-grounded question answering
4.  Decision/task extraction
5.  Catch-up generation
6.  Handoff package generation

The AI should not be treated as an authoritative source when the project
context does not contain enough information.

------------------------------------------------------------------------

## 12. Demo Scenario

Use a fictional engineering project such as:

**Smart Waste Management System**

Upload: - problem statement - component list - circuit image - meeting
notes

Gemini extracts: - objective - selected ESP32 - sensor choice - budget
constraint - completed research - pending prototype work

Then demonstrate:

1.  Ask: "Why did we choose ESP32?"
2.  Add: "We switched the backend to Firebase."
3.  Show the decision entering memory.
4.  Click "Catch Me Up".
5.  Generate the final handoff package.

------------------------------------------------------------------------

## 13. Future Vision

Future versions could add: - team accounts - real-time collaboration -
GitHub integration - Slack/Discord integration - Google Drive
integration - automatic meeting transcription - project timeline
visualization - semantic search - change detection - role-aware
handoffs - automatic onboarding for new members

------------------------------------------------------------------------

## 14. One-Sentence Pitch

> **HANDOFF preserves the context behind collaborative work, so when
> someone joins, leaves, or returns to a project, they can continue
> without starting from zero.**
