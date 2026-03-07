"""API router for photo management (upload, list, delete)."""

import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from loguru import logger
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.metrics import photos_uploaded_total
from app.models.photos import Photo

router = APIRouter(prefix="/api/photos", tags=["photos"])

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"
THUMBNAILS_DIR = UPLOADS_DIR / "thumbnails"
ALLOWED_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
THUMBNAIL_WIDTH = 200  # pixels

# Magic bytes: JPEG starts with FF D8 FF; PNG starts with 89 50 4E 47
_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
}


def _detect_type(data: bytes) -> str | None:
    for magic, mime in _MAGIC.items():
        if data[: len(magic)] == magic:
            return mime
    return None


def _generate_thumbnail(image_data: bytes, filename: str) -> None:
    """Generate thumbnail (200px wide) from image data."""
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    # Open image and create thumbnail
    img = Image.open(BytesIO(image_data))

    # Convert RGBA to RGB if needed (for PNG with transparency)
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
        img = background  # type: ignore[assignment]
    elif img.mode != "RGB":
        img = img.convert("RGB")  # type: ignore[assignment]

    # Calculate thumbnail size maintaining aspect ratio
    width, height = img.size
    new_width = THUMBNAIL_WIDTH
    new_height = int((new_width / width) * height)

    # Create thumbnail
    img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)

    # Save thumbnail
    thumb_path = THUMBNAILS_DIR / filename
    img.save(thumb_path, "JPEG", quality=85, optimize=True)

    logger.debug("Thumbnail generated: {}", thumb_path)


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
            "thumbnail_url": f"/static/uploads/thumbnails/{p.filename}",
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
        raise HTTPException(422, "Alleen JPG en PNG bestanden zijn toegestaan.")

    data = await file.read()

    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(422, f"Bestand te groot (max {MAX_SIZE_BYTES // 1024 // 1024} MB).")

    actual_type = _detect_type(data)
    if actual_type not in ALLOWED_TYPES:
        raise HTTPException(422, "Bestandsinhoud herkend niet als JPG of PNG.")

    ext = ".jpg" if actual_type == "image/jpeg" else ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOADS_DIR / filename
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)

    # Generate thumbnail
    try:
        _generate_thumbnail(data, filename)
    except Exception as e:
        logger.error("Failed to generate thumbnail for {}: {}", filename, e)
        # Continue even if thumbnail fails

    display_name = Path(file.filename).stem if file.filename else filename
    photo = Photo(filename=filename, display_name=display_name)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    logger.info("photos.uploaded id={} filename='{}' (with thumbnail)", photo.id, filename)
    photos_uploaded_total.inc()
    return {
        "id": photo.id,
        "filename": photo.filename,
        "display_name": photo.display_name,
        "url": f"/static/uploads/{photo.filename}",
        "thumbnail_url": f"/static/uploads/thumbnails/{photo.filename}",
        "uploaded_at": photo.uploaded_at.isoformat(),
    }


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(404, "Foto niet gevonden")

    # Delete original photo
    path = UPLOADS_DIR / photo.filename
    if path.exists():
        path.unlink()

    # Delete thumbnail
    thumb_path = THUMBNAILS_DIR / photo.filename
    if thumb_path.exists():
        thumb_path.unlink()

    await db.delete(photo)
    await db.commit()
    logger.info("photos.deleted id={} filename='{}' (including thumbnail)", photo_id, photo.filename)
