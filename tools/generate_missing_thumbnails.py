"""
Generate thumbnails for existing photos that don't have one yet.
Run this script after upgrading to add thumbnails for existing photos.

Usage: python generate_missing_thumbnails.py
"""

import asyncio
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models.photos import Photo

UPLOADS_DIR = Path(__file__).resolve().parent / "app" / "static" / "uploads"
THUMBNAILS_DIR = UPLOADS_DIR / "thumbnails"
THUMBNAIL_WIDTH = 200


def generate_thumbnail(image_path: Path, output_path: Path) -> bool:
    """Generate thumbnail from image file."""
    try:
        # Open and process image
        img = Image.open(image_path)

        # Convert RGBA to RGB if needed
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Calculate thumbnail size
        width, height = img.size
        new_width = THUMBNAIL_WIDTH
        new_height = int((new_width / width) * height)

        # Create thumbnail
        img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "JPEG", quality=85, optimize=True)

        return True
    except Exception as e:
        print(f"  [ERROR] Failed to generate thumbnail: {e}")
        return False


async def main():
    """Generate missing thumbnails for all photos."""
    print("Generating missing thumbnails...")
    print()

    await init_db()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Photo))
        photos = result.scalars().all()

        if not photos:
            print("No photos found in database.")
            return

        print(f"Found {len(photos)} photos in database")
        print()

        generated = 0
        skipped = 0
        errors = 0

        for photo in photos:
            original_path = UPLOADS_DIR / photo.filename
            thumb_path = THUMBNAILS_DIR / photo.filename

            # Check if original exists
            if not original_path.exists():
                print(f"[!] Original not found: {photo.filename}")
                errors += 1
                continue

            # Check if thumbnail already exists
            if thumb_path.exists():
                print(f"[-] Already exists: {photo.filename}")
                skipped += 1
                continue

            # Generate thumbnail
            print(f"[*] Generating: {photo.filename}...", end=" ")
            if generate_thumbnail(original_path, thumb_path):
                print("[OK]")
                generated += 1
            else:
                errors += 1

    print()
    print("=" * 50)
    print(f"[+] Generated: {generated}")
    print(f"[-] Skipped:   {skipped}")
    print(f"[!] Errors:    {errors}")
    print(f"[=] Total:     {len(photos)}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
