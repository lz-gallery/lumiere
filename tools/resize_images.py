from pathlib import Path
from PIL import Image, ImageOps

# ---------------- CONFIG ----------------
BASE_DIR = Path(__file__).parent.parent
INCOMING_DIR = BASE_DIR / "incoming"

MAX_SIZE = (4000, 4000)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# ----------------------------------------

files = sorted([f for f in INCOMING_DIR.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS])

if not files:
    print("No images found in /incoming")
else:
    print(f"Found {len(files)} image(s). Resizing to max 4000px on long edge...\n")
    for img_path in files:
        with Image.open(img_path) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size

            if max(w, h) <= 4000:
                print(f"⏭️  Skipping {img_path.name} ({w}×{h}, already within limit)")
                continue

            img.thumbnail(MAX_SIZE)
            img.convert("RGB").save(img_path, "JPEG", quality=95)
            new_w, new_h = img.size
            print(f"✅ {img_path.name}: {w}×{h} → {new_w}×{new_h}")

    print("\nDone.")
