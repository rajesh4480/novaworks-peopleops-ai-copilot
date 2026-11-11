# CB Nest AI Copilot
## Implementation Inventory

This inventory maps the AI Copilot capabilities to the source files present in the reviewed source archive. It is intended as a code-navigation reference for engineering review and ongoing maintenance.

## 1. Frontend

| Area | Source file | Responsibility |
|---|---|---|
| AI Usage Dashboard | `frontend/app/ai-usage/page.tsx` | Administrator-facing AI usage metrics and refresh flow |
| AI Copilot | `frontend/app/copilot/page.tsx` | Conversational interface, streaming response handling, message history, policy upload interaction and action confirmations |
| Sidebar navigation | `frontend/components/layout/sidebar.tsx` | Navigation entries for AI Copilot and admin-only AI Usage |
| API client | `frontend/lib/api.ts` | Typed frontend API requests, including streamed Copilot requests and AI analytics |
| Application layout | `frontend/app/layout.tsx` | Root frontend layout |
| Global styling | `frontend/app/globals.css` | Shared application styles |
| Frontend dependencies | `frontend/package.json` | Next.js, React, TypeScript and UI dependencies |

### Frontend routes

| Route | Page |
|---|---|
| `/copilot` | AI HR Copilot |
| `/ai-usage` | AI Usage Dashboard |

The sidebar marks AI Usage as `adminOnly`. The dashboard page also checks the role in the access token before requesting analytics. This client-side check is a presentation guard; the backend analytics endpoint independently enforces the administrator role.

## 2. Backend API

| Source file | Responsibility |
|---|---|
| `backend/app/api/v1/router.py` | Registers the chat and AI usage routers |
| `backend/app/api/v1/endpoints/chat.py` | Chat sessions, policy, SQL, action, confirmation, unified router and streaming endpoints |
| `backend/app/api/v1/endpoints/ai_usage.py` | Administrator-only aggregate AI usage analytics |
| `backend/app/core/security.py` | Authentication/security primitives |
| `backend/app/services/auth.py` | Authentication dependencies and role checks |
| `backend/app/core/config.py` | Application and database settings |

### AI endpoint map

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/chat/sessions` | Create a chat session |
| `POST` | `/api/v1/chat/sessions/{session_id}/messages` | Add a message to a session |
| `POST` | `/api/v1/chat/sql` | SQL Agent request |
| `POST` | `/api/v1/chat/policy` | Policy RAG request |
| `POST` | `/api/v1/chat/actions` | HR Action Agent request |
| `POST` | `/api/v1/chat/actions/confirmations/{confirmation_id}/confirm` | Confirm a pending high-impact action |
| `POST` | `/api/v1/chat/actions/confirmations/{confirmation_id}/cancel` | Cancel a pending high-impact action |
| `POST` | `/api/v1/chat/router` | Unified Copilot routing |
| `POST` | `/api/v1/chat/router/stream` | Streaming Copilot response |
| `GET` | `/api/v1/ai-usage/analytics` | Administrator-only AI usage analytics |

The endpoint names are taken from the registered FastAPI route definitions in the reviewed source files.

## 3. Database Models and Migrations

### AI audit model

| Item | Source |
|---|---|
| ORM model | `backend/app/models/ai_audit_log.py` |
| Table | `ai_audit_logs` |
| Initial migration | `backend/alembic/versions/0017_ai_audit_logs.py` |
| Latency migration | `backend/alembic/versions/bdfc4f3d0ad9_add_ai_audit_latency.py` |

The audit model records `user_id`, `role`, `message`, `intent`, `tool_name`, `action_status`, `records_accessed`, optional `latency_ms`, and `created_at`.

### Human-in-the-loop confirmation model

| Item | Source |
|---|---|
| ORM model | `backend/app/models/hitl_confirmation.py` |
| Table | `pending_action_confirmations` |
| Migration | `backend/alembic/versions/0018_pending_action_confirmations.py` |
| Service | `backend/app/services/ai/hitl_service.py` |

The model stores a user-bound confirmation token, action type, request question, status, creation/expiry timestamps, confirmation/completion timestamps, and an optional error message.

### Policy semantic cache

| Item | Implementation |
|---|---|
| Service | `backend/app/services/ai/semantic_cache.py` |
| Storage | Separate SQLite file at `backend/storage/hr_policy_semantic_cache.sqlite3` |
| Table | `policy_semantic_cache` |
| ORM model | None in the reviewed source |
| Alembic migration | None in the reviewed source; table and compatibility columns are created/updated by the cache service |

The cache stores the question, embedding JSON, answer, source JSON, creation timestamp, cache version, topic key and intent key. It uses a 24-hour default TTL, a default similarity threshold of `0.68`, and a cache version default of `2`. These defaults can be overridden by `HR_POLICY_CACHE_TTL_SECONDS`, `HR_POLICY_CACHE_THRESHOLD`, and `HR_POLICY_CACHE_VERSION`.

Semantic matches are restricted to compatible known topic and intent labels. Exact normalized question matches are also supported. The cache stores only answers with non-empty source references; cache failures are treated as non-fatal so they do not stop Policy RAG.

## 4. Schemas

| Source file | Relevant definitions |
|---|---|
| `backend/app/schemas/ai.py` | `AIChatRequest`, `PolicyChatResponse`, `SQLChatResponse`, `ActionChatResponse` |
| `backend/app/schemas/chat.py` | `ChatSessionCreate`, `ChatMessageCreate` |

The active endpoint handlers in `chat.py` use the chat schemas for message/session requests. The AI schemas provide typed AI request/response structures. Endpoint-specific response dictionaries should be checked against the handler implementation when preparing external API contracts.

## 5. AI Services

| Source file | Responsibility |
|---|---|
| `services/ai/router.py` | Intent classification and semantic routing |
| `services/ai/orchestration_graph.py` | LangGraph state graph that routes to policy, SQL, action or unsupported handling |
| `services/ai/policy_rag_service.py` | Policy question answering and streaming |
| `services/ai/policy_retriever.py` | Policy retrieval |
| `services/ai/vector_store.py` | Qdrant local store and hybrid dense/sparse vector configuration |
| `services/ai/embeddings.py` | Embedding setup |
| `services/ai/policy_indexer.py` | Policy indexing |
| `services/ai/policy_documents.py` | Policy document handling |
| `services/ai/policy_document_loader.py` | Policy file loading |
| `services/ai/policy_rag_evaluator.py` | Policy RAG evaluation logic |
| `services/ai/policy_rag_eval_dataset.py` | Evaluation dataset definitions |
| `services/ai/sql_agent.py` | SQL Agent logic |
| `services/ai/sql_generator.py` | SQL generation |
| `services/ai/sql_parser.py` | SQL parsing |
| `services/ai/sql_guardrails.py` | SQL safety validation |
| `services/ai/sql_authorization.py` | SQL authorization rules |
| `services/ai/sql_scope.py` | SQL scope handling |
| `services/ai/sql_scope_enforcer.py` | SQL scope enforcement |
| `services/ai/sql_scope_transformer.py` | SQL scope transformation |
| `services/ai/sql_question_guard.py` | SQL question validation |
| `services/ai/sql_service.py` | SQL question service entry point |
| `services/ai/action_agent.py` | HR action interpretation and execution |
| `services/ai/api_tools.py` | Existing HRMS API tool wrappers |
| `services/ai/permissions.py` | Role permission helpers |
| `services/ai/hitl_service.py` | Persistent confirmation lifecycle |
| `services/ai/audit_logger.py` | Persistent audit record creation, message redaction and retry handling |
| `services/ai/semantic_cache.py` | Policy answer cache |
| `services/ai/langsmith_tracing.py` | LangSmith trace configuration and token usage metadata |
| `services/ai/llm_provider.py` | Provider abstraction and environment-based provider selection |
| `services/ai/providers/groq_provider.py` | Groq provider implementation |
| `services/ai/providers/openai_provider.py` | OpenAI provider implementation |

## 6. Model and Retrieval Configuration

### LLM provider configuration

The provider abstraction reads these environment variables:

| Variable | Default / purpose |
|---|---|
| `LLM_PROVIDER` | Defaults to `groq`; supports `groq` and `openai` |
| `GROQ_API_KEY` | Groq API credential |
| `GROQ_MODEL` | Defaults to `llama-3.3-70b-versatile` |
| `OPENAI_API_KEY` | OpenAI API credential |
| `OPENAI_MODEL` | Defaults to `gpt-4o-mini` |

The supplied `backend/.env.example` does not currently list these LLM variables. Add them to deployment configuration as needed; do not add secret values to the repository.

### Policy vector store

| Setting | Value in source |
|---|---|
| Qdrant path | `backend/qdrant_storage` (constant in `vector_store.py`) |
| Collection | `hr_policy` |
| Dense model | `sentence-transformers/all-MiniLM-L6-v2` |
| Sparse model | `Qdrant/bm25` |
| Retrieval mode | Hybrid dense and sparse |

### LangSmith configuration

| Variable | Purpose |
|---|---|
| `LANGSMITH_TRACING` | Enables tracing when set to a truthy value |
| `LANGSMITH_API_KEY` | LangSmith API credential |

The LangSmith integration is best-effort: token-usage and trace recording errors are handled so they do not break a model response.

## 7. Authorization and Audit Boundaries

- `GET /api/v1/ai-usage/analytics` uses the backend `require_roles(Role.ADMIN)` dependency.
- The frontend also hides AI Usage from non-admin users, but backend authorization is the security boundary.
- The audit logger redacts common email, PAN, labeled credential, bank-account and Aadhaar-like patterns before storing the message.
- Audit writes use a separate database session and retry transient SQLite lock errors; audit logging is best-effort and does not intentionally fail the Copilot request if audit persistence fails.
- LangSmith tracing and the `ai_audit_logs` application table serve different purposes.
- The semantic cache is a separate SQLite store and is not represented by a SQLAlchemy ORM model in the reviewed source.

## 8. Database Session and Alembic Environment

The additional database files supplied for review confirm:

| File | Responsibility |
|---|---|
| `backend/app/db/session.py` | Creates the async SQLAlchemy engine and `SessionLocal`; exposes the `get_db()` dependency |
| `backend/app/db/base.py` | Defines the SQLAlchemy `DeclarativeBase` used as Alembic metadata |
| `backend/alembic/env.py` | Configures online/offline migrations, reads `DATABASE_URL`, removes the `+aiosqlite` driver marker for synchronous Alembic, and assigns `Base.metadata` to `target_metadata` |

**Migration metadata observation:** The supplied `env.py` imports a fixed list of standard HRMS model modules. The reviewed `backend/app/models/__init__.py` also exports the standard HRMS models but does not import `ai_audit_log` or `hitl_confirmation`. The AI tables are created by explicit versioned migrations, so those migrations are documented as the creation mechanism. However, the AI ORM models are not visibly registered in the supplied Alembic metadata import path. Before relying on Alembic autogenerate for future changes to these AI models, import/register both AI model modules before `target_metadata = Base.metadata` and verify the generated metadata. This is a maintenance observation, not a claim that the existing migrations failed.

## 9. Automated Test Coverage and Source Review Scope

The supplied source archive did **not** contain a `backend/tests/` directory or a dedicated backend test folder. Therefore this documentation does not claim that every backend file has an associated automated test, nor does it claim that the complete backend suite was run from this archive.

The historical test counts recorded in the evaluation report were supplied during earlier project testing and are identified there as previously reported runs. They are not independently reproducible from the source ZIP because the test files and test configuration were not included.

The reviewed material includes the frontend pages/components/API client, selected backend API, model, schema, service, migration, configuration and dependency files, plus the subsequently supplied `session.py`, `base.py`, `env.py`, and `.env.example`.

The source archive also contained `policy_document_loader - Copy.py`; it is not treated as an active production module in this inventory.

