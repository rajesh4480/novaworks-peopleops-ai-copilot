![CB Nest Logo](./logo.png)

# CB Nest

**CB Nest** is a full-stack HR Management System built for hands-on learning. It covers real-world business workflows — employee lifecycle, attendance, leave approvals, payroll, ticketing, and more — using a modern stack (FastAPI + Next.js + Docker). Use it to understand how production-grade HRMS platforms work, and extend it with your own AI features.

> 📖 **New here?** Start with the [Learner Guide](docs/Learner_Guide.md) for a complete walkthrough of the project architecture, database, and how to explore the code.

## Overview

This project provides a working HRMS platform with authentication, employee operations, attendance, leave management, communication features, finance data views, and ticketing workflows.

It is designed as a practical base for AI feature integration (RAG, assistants, agent workflows) without rebuilding core HR modules from scratch.

## Tech Stack

- Frontend: Next.js 15, React 19, Tailwind CSS
- Backend: FastAPI, SQLAlchemy (async), Pydantic v2
- Database: SQLite
- Migrations: Alembic
- Orchestration: Docker Compose

## Features

- JWT auth with role-aware access (ADMIN, MANAGER, EMPLOYEE)
- Employee directory with search, filters, and pagination
- Attendance clock in/clock out with status and mode tracking
- Leave balances and leave request workflow
- Announcements and polls
- Team calendar (leaves, WFH, holidays, birthdays)
- My Profile edits, profile photo upload, job history, documents
- Finance views (salary, statutory, payroll history)
- Tickets with assignment, status updates, onboarding tasks
- HR policy upload/download library
- Admin/Manager employee document upload flow (APPOINTMENT, TAX, PAYSLIP, OTHER)
- My Documents with search, view, and download; delete is allowed only for `OTHER` document type
- Password-protected PDF payslips (DOB in `DD-MM-YY`) for generated and uploaded payslips
- Notification bell for announcements, polls, ticket assignment, ticket status, leave decision, and employee-document uploads by others (not self-uploads)
- Integrated AI HR Copilot: Policy RAG, read-only SQL Agent, and HR Action Agent

## Repository Structure

The repository is organized by application layer. The tree below shows the main application modules and the complete migration, model, schema, and service files reviewed for this codebase. It is a navigational overview rather than an exhaustive listing of every UI component or static asset.

```text
.
|-- backend/
|   |-- alembic/
|   |   |-- versions/
|   |   |   |-- 0001_initial.py
|   |   |   |-- 0002_leave_workflow.py
|   |   |   |-- 0003_announcements.py
|   |   |   |-- 0004_ticket_management.py
|   |   |   |-- 0005_phase3_finance_engagement_ai.py
|   |   |   |-- 0006_calendar_real_data.py
|   |   |   |-- 0007_attendance_mode_punctuality.py
|   |   |   |-- 0008_skills_projects_recommendations.py
|   |   |   |-- 0009_hr_policy_file_meta.py
|   |   |   |-- 0010_employee_profile_photo.py
|   |   |   |-- 0011_employee_finance_profile.py
|   |   |   |-- 0012_remove_business_units.py
|   |   |   |-- 0013_employee_documents.py
|   |   |   |-- 0014_project_status.py
|   |   |   |-- 0015_half_day_leave_support.py
|   |   |   |-- 0016_employee_documents_uploaded_by.py
|   |   |   |-- 0017_ai_audit_logs.py
|   |   |   |-- 0018_pending_action_confirmations.py
|   |   |   `-- bdfc4f3d0ad9_add_ai_audit_latency.py
|   |   `-- env.py
|   |-- app/
|   |   |-- api/v1/
|   |   |   |-- endpoints/
|   |   |   |   |-- announcements.py
|   |   |   |   |-- ai_usage.py
|   |   |   |   |-- attendance.py
|   |   |   |   |-- auth.py
|   |   |   |   |-- chat.py
|   |   |   |   |-- employees.py
|   |   |   |   |-- finance.py
|   |   |   |   |-- health.py
|   |   |   |   |-- hr_policies.py
|   |   |   |   |-- leaves.py
|   |   |   |   |-- org.py
|   |   |   |   |-- polls.py
|   |   |   |   |   |-- team_calendar.py
|   |   |   |   `-- tickets.py
|   |   |   `-- router.py
|   |   |-- core/
|   |   |   |-- config.py
|   |   |   |-- logging.py
|   |   |   |-- response.py
|   |   |   `-- security.py
|   |   |-- db/
|   |   |   |-- base.py
|   |   |   `-- session.py
|   |   |-- models/
|   |   |   |-- announcement.py
|   |   |   |-- attendance_log.py
|   |   |   |-- department.py
|   |   |   |-- employee.py
|   |   |   |-- employee_document.py
|   |   |   |-- employee_project.py
|   |   |   |-- employee_skill.py
|   |   |   |-- enums.py
|   |   |   |-- holiday.py
|   |   |   |-- hr_policy.py
|   |   |   |-- job_history.py
|   |   |   |-- leave_balance.py
|   |   |   |-- leave_request.py
|   |   |   |-- onboarding_task.py
|   |   |   |-- payroll_record.py
|   |   |   |-- poll.py
|   |   |   |-- poll_response.py
|   |   |   |-- project.py
|   |   |   |-- skill.py
|   |   |   |-- ticket.py
|   |   |   |-- ai_audit_log.py
|   |   |   `-- hitl_confirmation.py
|   |   |-- schemas/
|   |   |   |-- announcement.py
|   |   |   |-- attendance.py
|   |   |   |-- auth.py
|   |   |   |-- common.py
|   |   |   |-- employee.py
|   |   |   |-- leave.py
|   |   |   |-- poll.py
|   |   |   |-- ticket.py
|   |   |   |-- ai.py
|   |   |   `-- chat.py
|   |   `-- services/
|   |       |-- auth.py
|   |       `-- ai/
|   |           |-- action_agent.py
|   |           |-- api_tools.py
|   |           |-- audit.py
|   |           |-- audit_logger.py
|   |           |-- embeddings.py
|   |           |-- hitl_service.py
|   |           |-- langsmith_tracing.py
|   |           |-- llm_provider.py
|   |           |-- orchestration_graph.py
|   |           |-- permissions.py
|   |           |-- policy_documents.py
|   |           |-- policy_document_loader.py
|   |           |-- policy_indexer.py
|   |           |-- policy_rag.py
|   |           |-- policy_rag_evaluator.py
|   |           |-- policy_rag_eval_dataset.py
|   |           |-- policy_rag_service.py
|   |           |-- policy_retriever.py
|   |           |-- router.py
|   |           |-- semantic_cache.py
|   |           |-- sql_agent.py
|   |           |-- sql_authorization.py
|   |           |-- sql_generator.py
|   |           |-- sql_guardrails.py
|   |           |-- sql_parser.py
|   |           |-- sql_prompts.py
|   |           |-- sql_question_guard.py
|   |           |-- sql_scope.py
|   |           |-- sql_scope_enforcer.py
|   |           |-- sql_scope_transformer.py
|   |           |-- sql_service.py
|   |           |-- ticket_action_selector.py
|   |           |-- vector_store.py
|   |           `-- providers/
|   |               |-- groq_provider.py
|   |               `-- openai_provider.py
|   |-- scripts/
|   |   |-- migrate_payslips_to_encrypted_pdf.py
|   |   `-- seed.py
|   |-- storage/
|   |   |-- hr-policies/
|   |   |-- profile-photos/
|   |   `-- qdrant_storage/              # local vector-store data
|   |-- .env.example
|   |-- alembic.ini
|   |-- Dockerfile
|   `-- requirements.txt
|-- frontend/
|   |-- app/
|   |   |-- ai-usage/page.tsx
|   |   |-- announcements/page.tsx
|   |   |-- attendance/page.tsx
|   |   |-- copilot/page.tsx
|   |   |-- dashboard/page.tsx
|   |   |-- employees/page.tsx
|   |   |-- employees/new/page.tsx
|   |   |-- employees/payslips/page.tsx
|   |   |-- employees/projects/page.tsx
|   |   |-- finance/page.tsx
|   |   |-- hr-policies/page.tsx
|   |   |-- leaves/page.tsx
|   |   |-- login/page.tsx
|   |   |-- me/page.tsx
|   |   |-- me/documents/page.tsx
|   |   |-- organization/page.tsx
|   |   |-- polls/page.tsx
|   |   |-- team-calendar/page.tsx
|   |   |-- tickets/page.tsx
|   |   |-- layout.tsx
|   |   `-- page.tsx
|   |-- components/
|   |   |-- layout/
|   |   |   |-- notification-bell.tsx
|   |   |   |-- sidebar.tsx
|   |   |   `-- topbar.tsx
|   |   `-- ui/
|   |       |-- badge.tsx
|   |       |-- button.tsx
|   |       |-- card.tsx
|   |       |-- date-picker.tsx
|   |       |-- input.tsx
|   |       |-- label.tsx
|   |       |-- rich-text.tsx
|   |       `-- table.tsx
|   |-- lib/
|   |   |-- api.ts
|   |   |-- date.ts
|   |   `-- utils.ts
|   |-- Dockerfile
|   |-- middleware.ts
|   `-- package.json
|-- docs/
|   |-- api/
|   |-- evidence/
|   |   |-- ai-dashboard/
|   |   `-- audit-log/
|   |-- Learner_Guide.md
|   |-- PRD.md
|   |-- db_tables_samples.md
|   |-- ai_architecture.md
|   |-- ai_architecture_flow.png
|   |-- ai_implementation_inventory.md
|   |-- ai_permissions_matrix.md
|   `-- ai_eval_results.md
|-- docker-compose.yml
`-- README.md
```

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose v2)
  - On Windows: install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and ensure the **WSL 2 backend** is enabled
- **Git**

## Quick Start

First-time setup:

```bash
git clone <repo-url>
cd HRMS
cp backend/.env.example backend/.env
```

For PowerShell on Windows:

```powershell
Copy-Item backend/.env.example backend/.env
```

Then run from repository root:

```bash
docker-compose up -d --build
docker-compose exec api alembic -c alembic.ini upgrade head
docker-compose exec api python scripts/seed.py
```

Open:

- App: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- API redoc: `http://localhost:8000/redoc`

Verify everything is working:

```bash
docker-compose ps
```

## Default Credentials

- Admin: `admin@mock-hrms.dev` / `password123`
- Manager: `manager@mock-hrms.dev` / `password123`
- Employee: `employee@mock-hrms.dev` / `password123`

## Configuration

Backend environment file: `backend/.env`

Use `backend/.env.example` as reference. Current key settings:

- `DATABASE_URL=sqlite+aiosqlite:///./storage/hrms.db`
- `APP_TIMEZONE=Asia/Kolkata`
- JWT settings (`JWT_SECRET_KEY`, expiry values)
- AI provider settings (`LLM_PROVIDER`, `GROQ_API_KEY`, `GROQ_MODEL`, `OPENAI_API_KEY`, `OPENAI_MODEL`)
- Optional LangSmith tracing settings (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`)

Set actual credentials in the local `.env` file. Never commit secrets. The AI vector store currently uses the local `backend/qdrant_storage` path configured in its service code.

## Common Commands

Start services:

```bash
docker-compose up -d
```

Restart API + Web after code changes:

```bash
docker compose restart api web
```

Stop services:

```bash
docker-compose down
```

Run migrations:

```bash
docker-compose exec api alembic -c alembic.ini upgrade head
```

Reseed data:

```bash
docker-compose exec api python scripts/seed.py
```

Optional one-time migration (legacy payslip files to DOB-password-protected PDFs):

```bash
docker compose exec api python scripts/migrate_payslips_to_encrypted_pdf.py
```

Check containers:

```bash
docker-compose ps
```

## Reset Database

On macOS/Linux:

```bash
docker-compose down
rm -f backend/storage/hrms.db
docker-compose up -d --build
docker-compose exec api alembic -c alembic.ini upgrade head
docker-compose exec api python scripts/seed.py
```

On PowerShell:

```powershell
docker-compose down
Remove-Item backend\storage\hrms.db -Force -ErrorAction SilentlyContinue
docker-compose up -d --build
docker-compose exec api alembic -c alembic.ini upgrade head
docker-compose exec api python scripts/seed.py
```

## API Notes

- API base path: `/api/v1`
- Health checks: `/health` and `/api/v1/health`
- Standard response envelope:
  - Success: `{ "success": true, "data": ..., "error": null }`
  - Error: `{ "success": false, "data": null, "error": { "code": "...", "message": "..." } }`
- Document uploads:
  - Employee self-upload: `POST /api/v1/employees/me/documents`
  - Employee self-delete: `DELETE /api/v1/employees/me/documents/{document_id}` (`OTHER` type only)
  - Admin/Manager upload for any employee: `POST /api/v1/employees/{employee_id}/documents`
  - Admin/Manager payslip upload: `POST /api/v1/employees/{employee_id}/documents/payslip`

## Troubleshooting

- If frontend shows stale build/runtime issues: `docker-compose restart web`
- If API changes are not reflected: `docker-compose restart api`
- If migration or seed fails: reset the database using the commands above, then migrate and seed again.

## Documentation

- [Learner Guide](docs/Learner_Guide.md) — project walkthrough, architecture, database schema, and development workflow
- [Product Requirements](docs/PRD.md)
- [Database Schema Reference](docs/db_tables_samples.md)
- [API contracts](docs/api/)

## Project Demo

Watch the NovaWorks PeopleOps AI Copilot demonstration:

[![NovaWorks PeopleOps Demo](https://img.youtube.com/vi/ZxcmfVHWrdM/0.jpg)](https://www.youtube.com/watch?v=ZxcmfVHWrdM)

**YouTube:** https://youtu.be/ZxcmfVHWrdM  
**Duration:** 7 minutes 48 seconds

The demonstration covers the integrated Policy RAG Assistant, read-only SQL Agent, HR Action Agent, role-based access controls, human-in-the-loop confirmations, streaming responses, AI Usage Dashboard, and LangSmith tracing.

---

---

## AI Copilot

The AI Copilot is one integrated capability within the wider CB Nest HRMS. It does not replace the existing HR modules. It connects policy knowledge, authorized HR data queries, and supported HR workflows to the existing authenticated application.

### Capabilities

- **Policy RAG:** hybrid retrieval over the HR policy collection with source-grounded answers and abstention when the available policy content is insufficient.
- **Read-only SQL Agent:** generates and validates HR data queries, applies authorization and data-scope controls, and blocks unsafe or destructive SQL.
- **HR Action Agent:** invokes supported existing backend API operations rather than writing directly to business tables.
- **Role-based access:** applies Employee, Manager, and Admin permissions on the backend.
- **Human-in-the-loop confirmation:** provides confirm/cancel flows for configured high-impact actions.
- **Unified orchestration and streaming:** routes requests to the relevant capability and exposes a streaming endpoint.
- **Audit and analytics:** persists AI interaction/action audit records and provides an administrator-only AI usage dashboard.
- **Tracing and caching:** supports LangSmith tracing and a separate semantic cache for eligible policy responses.

### AI frontend

- Copilot: [`frontend/app/copilot/page.tsx`](frontend/app/copilot/page.tsx)
- AI Usage Dashboard: [`frontend/app/ai-usage/page.tsx`](frontend/app/ai-usage/page.tsx)
- Navigation integration: [`frontend/components/layout/sidebar.tsx`](frontend/components/layout/sidebar.tsx)
- Shared API client: [`frontend/lib/api.ts`](frontend/lib/api.ts)

### AI backend and API routes

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/chat/sessions` | Create a chat session |
| `POST` | `/api/v1/chat/sessions/{session_id}/messages` | Add a message to a session |
| `POST` | `/api/v1/chat/sql` | Read-only HR data query |
| `POST` | `/api/v1/chat/policy` | Policy RAG question answering |
| `POST` | `/api/v1/chat/actions` | HR workflow action request |
| `POST` | `/api/v1/chat/actions/confirmations/{confirmation_id}/confirm` | Confirm a pending action |
| `POST` | `/api/v1/chat/actions/confirmations/{confirmation_id}/cancel` | Cancel a pending action |
| `POST` | `/api/v1/chat/router` | Unified Copilot routing |
| `POST` | `/api/v1/chat/router/stream` | Streaming Copilot response |
| `GET` | `/api/v1/ai-usage/analytics` | Administrator-only AI usage analytics |

### AI data and persistence

- `ai_audit_logs` stores AI interaction and action audit metadata; schema changes are managed by the AI audit migrations.
- `pending_action_confirmations` stores pending human confirmation state for supported actions.
- `policy_semantic_cache` is stored in a separate SQLite database file at `backend/storage/hr_policy_semantic_cache.sqlite3`; it is initialized by the cache service rather than an Alembic ORM migration.
- Policy vectors are stored in the local Qdrant path `backend/qdrant_storage`, using collection `hr_policy`, dense embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and sparse retrieval (`Qdrant/bm25`).

### AI documentation

- [AI Architecture](docs/ai_architecture.md) — components, request flow, data flow, and operational considerations
- [AI Permissions Matrix](docs/ai_permissions_matrix.md) — role and action permissions
- [AI Evaluation Results](docs/ai_eval_results.md) — evaluation criteria, test scenarios, evidence, and known limitations
- [AI Implementation Inventory](docs/ai_implementation_inventory.md) — source-file inventory and responsibilities
- [Architecture Flow Diagram](docs/ai_architecture_flow.png)
- [AI Dashboard Evidence](docs/evidence/ai-dashboard/)
- [Audit Log Evidence](docs/evidence/audit-log/)

### AI configuration

AI configuration is managed through `backend/.env`, using `backend/.env.example` as the starting point. Supported provider configuration includes `LLM_PROVIDER`, `GROQ_API_KEY`, `GROQ_MODEL`, `OPENAI_API_KEY`, and `OPENAI_MODEL`. LangSmith can be configured with `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT`. The semantic cache supports `HR_POLICY_CACHE_TTL_SECONDS`, `HR_POLICY_CACHE_THRESHOLD`, and `HR_POLICY_CACHE_VERSION` overrides. Do not commit populated credentials or secrets.

### AI safety boundaries

- SQL Agent access is read-only; destructive and write statements must be rejected.
- HR actions must use existing backend API tools and enforce backend authorization.
- Employees must not gain manager/admin capabilities through chat prompts.
- Sensitive employee data remains subject to the same role and record-scope restrictions as the HRMS APIs.
- A successful refusal or blocked unsafe request is a security outcome, not a failed functional operation.

---

Copyright (c) Codebasics. All rights reserved.
