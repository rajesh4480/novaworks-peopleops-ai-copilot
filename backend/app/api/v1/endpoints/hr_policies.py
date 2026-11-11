
import hashlib
import logging
from pathlib import Path
from uuid import uuid4
from app.services.ai.semantic_cache import invalidate_policy_semantic_cache
from app.services.ai.vector_store import delete_policy_vectors

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.response import success_response
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import Role
from app.models.hr_policy import HRPolicy
from app.services.ai.policy_documents import load_policy_as_documents
from app.services.ai.semantic_cache import invalidate_policy_semantic_cache
from app.services.ai.vector_store import get_vector_store
from app.services.auth import get_current_user, require_roles


logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_POLICY_EXTENSIONS = {".txt", ".md", ".pdf"}


@router.get("")
async def list_policies(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user

    total = (
        await db.execute(
            select(func.count(HRPolicy.id))
        )
    ).scalar_one()

    rows = (
        await db.execute(
            select(HRPolicy)
            .order_by(HRPolicy.id.asc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    return success_response(
        {
            "items": [
                {
                    "id": row.id,
                    "title": row.title,
                    "category": row.category,
                    # Legacy seeded rows may still use this.
                    "content": row.content,
                    "original_filename": row.original_filename,
                    "file_path": row.file_path,
                    "mime_type": row.mime_type,
                    "size_bytes": row.size_bytes,
                    "uploaded_by": row.uploaded_by,
                    "checksum": row.checksum,
                    "created_at": (
                        row.created_at.isoformat()
                        if row.created_at
                        else None
                    ),
                }
                for row in rows
            ],
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        }
    )


@router.post("/upload")
async def upload_policy_document(
    title: str = Form(min_length=3, max_length=220),
    category: str = Form(min_length=2, max_length=60),
    file: UploadFile = File(...),
    current_user: Employee = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
    db: AsyncSession = Depends(get_db),
):
    upload_dir = Path(settings.policy_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_POLICY_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt, .md, and .pdf are supported",
        )

    raw = await file.read()

    if len(raw) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 2 MB)",
        )

    if extension in {".txt", ".md"}:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only UTF-8 text is supported for .txt/.md",
            ) from exc

    stored_filename = f"{uuid4().hex}{extension}"
    stored_path = upload_dir / stored_filename
    stored_path.write_bytes(raw)

    checksum = hashlib.sha256(raw).hexdigest()

    mime_type = file.content_type or {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".pdf": "application/pdf",
    }.get(extension, "application/octet-stream")

    policy = HRPolicy(
        title=title.strip(),
        category=category.strip(),
        content=None,
        original_filename=file.filename,
        file_path=str(stored_path),
        mime_type=mime_type,
        size_bytes=len(raw),
        uploaded_by=current_user.id,
        checksum=checksum,
    )

    # Save the policy first so it has a database ID.
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    # Invalidate cached policy answers after a new policy is saved.
    invalidate_policy_semantic_cache()

    # Index only this policy. Do not rebuild the whole Qdrant collection.
    try:
        documents = load_policy_as_documents(
            path=policy.file_path,
            policy_id=policy.id,
            title=policy.title,
            category=policy.category,
            original_filename=policy.original_filename,
        )

        if not documents:
            raise ValueError(
                "The uploaded policy produced no text chunks."
            )

        vector_store = get_vector_store()
        vector_ids = vector_store.add_documents(documents)

        if not vector_ids:
            raise RuntimeError(
                "Qdrant did not return any indexed document IDs."
            )

        logger.info(
            "Indexed policy %s (%s): %s chunks",
            policy.id,
            policy.title,
            len(vector_ids),
        )

    except Exception as exc:
        logger.exception(
            "Policy %s was saved but indexing failed.",
            policy.id,
        )

        # The database record and uploaded file already exist.
        # Report the indexing failure clearly to the caller.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Policy {policy.id} was saved, but indexing failed. "
                "Check the backend logs for details."
            ),
        ) from exc

    return success_response(
        {
            "id": policy.id,
            "title": policy.title,
            "category": policy.category,
            "content": policy.content,
            "original_filename": policy.original_filename,
            "file_path": policy.file_path,
            "mime_type": policy.mime_type,
            "size_bytes": policy.size_bytes,
            "uploaded_by": policy.uploaded_by,
            "checksum": policy.checksum,
            "created_at": (
                policy.created_at.isoformat()
                if policy.created_at
                else None
            ),
        }
    )


@router.get("/{policy_id}/download")
async def download_policy_document(
    policy_id: int,
    _: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    policy = (
        await db.execute(
            select(HRPolicy).where(HRPolicy.id == policy_id)
        )
    ).scalar_one_or_none()

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    if not policy.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy file not available",
        )

    base_dir = Path(settings.policy_upload_dir).resolve()
    requested = Path(policy.file_path).resolve()

    if base_dir not in requested.parents and requested != base_dir:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path",
        )

    if not requested.exists() or not requested.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy file missing on server",
        )

    return FileResponse(
        path=str(requested),
        filename=policy.original_filename or requested.name,
        media_type=policy.mime_type or "application/octet-stream",
    )

@router.delete("/{policy_id}")
async def delete_policy_document(
    policy_id: int,
    current_user: Employee = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HRPolicy).where(HRPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    # Validate the stored path before touching the file.
    stored_path = None
    if policy.file_path:
        base_dir = Path(settings.policy_upload_dir).resolve()
        requested_path = Path(policy.file_path).resolve()

        if base_dir not in requested_path.parents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid policy file path",
            )

        stored_path = requested_path

    # Remove the policy's vectors first. If this fails, keep the DB row.
    try:
        delete_policy_vectors(policy_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Could not remove policy from the AI search index. "
                "The policy record was not deleted."
            ),
        ) from exc

    try:
        await db.delete(policy)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        # Qdrant deletion has already happened. Log and reconcile this
        # exceptional case rather than reporting a successful deletion.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The AI search index was updated, but the database deletion "
                "failed. The policy needs to be reindexed or reconciled."
            ),
        ) from exc

    # Only remove the file after the database deletion succeeds.
    if stored_path and stored_path.is_file():
        try:
            stored_path.unlink()
        except OSError:
            # The DB and vector index are deleted, but an orphaned file
            # may remain for manual cleanup.
            pass

    invalidate_policy_semantic_cache()

    return success_response(
        {
            "id": policy_id,
            "message": "Policy deleted from the library and AI search index.",
        }
    )
