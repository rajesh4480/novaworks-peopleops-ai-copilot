# Docker setup — CB Nest / NovaWorks PeopleOps

This setup is configured for **development**. It runs the FastAPI backend and
Next.js frontend, keeps SQLite uploads and the local Qdrant database in Docker
named volumes, and waits for the API health check before starting the frontend.

## Required project layout

Place the files in these exact locations:

- `docker-compose.yml` (project root)
- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/.env` (create from `backend/.env.docker.example`)
- `frontend/Dockerfile`
- `frontend/.dockerignore`

Keep the existing application source, `backend/requirements.txt`,
`frontend/package.json`, and frontend lockfile in place.

## First startup

1. Install Docker Desktop with WSL 2 support on a machine that has enough free
   disk space. The images and AI model files can be large.
2. Copy `backend/.env.docker.example` to `backend/.env`.
3. Set `JWT_SECRET_KEY` to a long random secret. Add either the Groq or OpenAI
   API key if you want the corresponding LLM provider to work. LangSmith
   credentials are optional.
4. From the project root, run:

   ```bash
   docker compose up --build -d
   ```

5. Open:
   - Frontend: http://localhost:3000
   - Backend API docs: http://localhost:8000/docs

## Data persistence

Docker named volumes retain these items across container recreation:

- `hrms_storage`: SQLite database, uploaded HR policies, employee documents,
  profile photos, and the semantic-cache SQLite file.
- `qdrant_storage`: local Qdrant vector database.
- `frontend_node_modules` and `frontend_next`: frontend dependencies/build cache.

Do not run `docker compose down -v` unless you intentionally want to delete
these named volumes and their stored data.

## Important notes

- The backend uses local persistent Qdrant storage; a separate Qdrant server
  container is not required by the current application configuration.
- `NEXT_PUBLIC_API_BASE_URL` is set to `http://localhost:8000` because the
  browser accesses the API through the host-published port.
- The backend health check verifies that the API process is accepting TCP
  connections on port 8000. It does not assume a particular health-route URL.
- The first image build and first AI request may take longer because Python
  dependencies and embedding/reranking model files may need to be downloaded.
  Internet access is required during build and first model initialization.
- This is not a production deployment. It uses development servers and source
  bind mounts. A production deployment should use non-reload Uvicorn workers,
  a production Next.js build/start command, HTTPS/reverse proxy, managed
  secrets, backups, and an appropriate database/storage strategy.
- Docker cannot be meaningfully verified on a PC where Docker is not installed.
  These files are prepared from the supplied project configuration, but the
  first build must be run on a Docker-capable machine.
