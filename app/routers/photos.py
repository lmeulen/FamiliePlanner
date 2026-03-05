"""API router for photo management (upload, list, delete)."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.photos import Photo

router = APIRouter(prefix="/api/photos", tags=["photos"])

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE_MB = 10


@router.get("/", response_model=list[dict])
async def list_photos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Photo).order_by(Photo.uploaded_at.desc()))
    photos = result.scalars().all()
    return [
        {
            "id": p.id,
            "filename": p.filename,
            "display_name": p.display_name,
            "url": f"/static/uploads/{p.filename}",
            "uploaded_at": p.uploaded_at.isoformat(),
        }
        for p in photos
    ]


@router.post("/", status_code=201, response_model=dict)
async def upload_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(422, f"Bestandstype niet toegestaan. Gebruik: {', '.join(ALLOWED_TYPES)}")

    data = await file.read()
    if len(data) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(422, f"Bestand te groot (max {MAX_SIZE_MB} MB).")

    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOADS_DIR / filename
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)

    display_name = Path(file.filename).stem if file.filename else filename
    photo = Photo(filename=filename, display_name=display_name)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    logger.info("photos.uploaded id={} filename='{}'", photo.id, filename)
    return {
        "id": photo.id,
        "filename": photo.filename,
        "display_name": photo.display_name,
        "url": f"/static/uploads/{photo.filename}",
        "uploaded_at": photo.uploaded_at.isoformat(),
    }


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(404, "Foto niet gevonden")
    path = UPLOADS_DIR / photo.filename
    if path.exists():
        path.unlink()
    await db.delete(photo)
    await db.commit()
    logger.info("photos.deleted id={} filename='{}'", photo_id, photo.filename)
