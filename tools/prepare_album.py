import json
import requests
import shutil
import base64
import re
import io
from pathlib import Path
from PIL import Image, ImageOps

# ---------------- CONFIG ----------------
API_KEY = "aa04a80fcfbeee801a105928b492f83a"
BASE_DIR = Path(__file__).parent.parent
INCOMING_DIR = BASE_DIR / "incoming"
DATA_DIR = BASE_DIR / "data"
IMAGE_ROOT = BASE_DIR / "images"
MENU_FILE = BASE_DIR / "menu.html"

THUMB_MAX_SIZE = (600, 600)
WEB_MAX_SIZE = (1800, 1800)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Ensure base directories exist
DATA_DIR.mkdir(exist_ok=True)
IMAGE_ROOT.mkdir(exist_ok=True)
INCOMING_DIR.mkdir(exist_ok=True)
# ----------------------------------------

def sanitize_filename(path):
    """Renames a file to remove spaces and special characters, returns new path."""
    clean_name = re.sub(r'[^\w.\-]', '_', path.name)
    clean_name = re.sub(r'_+', '_', clean_name)
    new_path = path.parent / clean_name
    if new_path != path:
        path.rename(new_path)
        print(f"  📝 Renamed '{path.name}' → '{clean_name}'")
    return new_path

def select_from_options(options, prompt):
    """Generates a numbered list in the terminal for selection."""
    print(f"\nAvailable {prompt}s:")
    for i, opt in enumerate(options, 1):
        print(f"[{i}] {opt}")
    choice = input(f"Select {prompt} (number) or press Enter to type new: ").strip()

    if not choice:
        return None
    try:
        return options[int(choice) - 1]
    except (ValueError, IndexError):
        return None

def upload_to_imgbb(image_bytes):
    """Uploads raw image bytes to imgbb and returns the URL or None."""
    url = "https://api.imgbb.com/1/upload"
    try:
        base64_image = base64.b64encode(image_bytes)
        payload = {"key": API_KEY, "image": base64_image}
        res = requests.post(url, data=payload, timeout=60)
        if res.status_code == 200:
            return res.json()['data']['url']
        else:
            error_msg = res.json().get('error', {}).get('message', res.text)
            print(f"  ⚠️  imgbb error {res.status_code}: {error_msg}")
            return None
    except requests.exceptions.Timeout:
        print(f"  ⚠️  Upload timed out")
        return None
    except Exception as e:
        print(f"  ⚠️  Upload failed: {e}")
        return None

def strip_source_fields(images_data, ALBUM_JSON):
    """Removes source_file from all entries and saves the clean JSON."""
    cleaned = [{k: v for k, v in item.items() if k != "source_file"} for item in images_data]
    with open(ALBUM_JSON, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)
    return cleaned

def rebuild_master_files():
    print("\nRefreshing master files...")
    structure = {}
    for year_folder in sorted(IMAGE_ROOT.iterdir()):
        if year_folder.is_dir() and year_folder.name.isdigit():
            year = year_folder.name
            structure[year] = []
            for album_folder in sorted(year_folder.iterdir()):
                if album_folder.is_dir() and (album_folder / "thumbs").exists():
                    album_slug = album_folder.name
                    display_name = album_slug.replace('_', ' ').upper()
                    structure[year].append({"title": display_name, "file": f"data/{year}/{album_slug}.json"})

    with open(DATA_DIR / "albums_list.json", "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2)

    menu_html = '<a onclick="showHome()">HOME</a>\n'
    for year in sorted(structure.keys(), reverse=True):
        menu_html += f'<div class="menu-year" onclick="toggleYear(\'year-{year}\')">{year} ▼</div>\n'
        menu_html += f'<div id="year-{year}" class="menu-albums" style="display:none;">\n'
        for album in structure[year]:
            menu_html += f'  <a onclick="loadAlbum(\'{album["file"]}\')">{album["title"]}</a>\n'
        menu_html += '</div>\n'

    with open(MENU_FILE, "w", encoding="utf-8") as f:
        f.write(menu_html)
    print("✅ Master files refreshed.")

def rename_album():
    years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
    if not years: return
    year = select_from_options(years, "Year")
    if not year: year = input("Enter Year: ").strip()

    album_options = sorted([d.name for d in (IMAGE_ROOT / year).iterdir() if d.is_dir()])
    old_name = select_from_options(album_options, "Album")
    if not old_name: return

    new_input = input(f"\nEnter NEW name for '{old_name}': ").strip()
    new_slug = new_input.lower().replace(" ", "_").replace("'", "")

    shutil.move(str(IMAGE_ROOT / year / old_name), str(IMAGE_ROOT / year / new_slug))
    old_json = DATA_DIR / year / f"{old_name}.json"
    if old_json.exists():
        shutil.move(str(old_json), str(DATA_DIR / year / f"{new_slug}.json"))
    print(f"✅ Renamed to '{new_slug}'")

def process_images():
    years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
    year = select_from_options(years, "Year")
    if not year:
        year = input("New Year (e.g. 2025): ").strip()

    albums = sorted([d.name for d in (IMAGE_ROOT / year).iterdir() if d.is_dir()]) if (IMAGE_ROOT / year).exists() else []
    album_slug = select_from_options(albums, "Album")
    if not album_slug:
        album_input = input("New Album Name: ").strip()
        album_slug = album_input.lower().replace(" ", "_").replace("'", "")

    ALBUM_ROOT = IMAGE_ROOT / year / album_slug
    ALBUM_THUMBS = ALBUM_ROOT / "thumbs"
    ALBUM_JSON = DATA_DIR / year / f"{album_slug}.json"

    ALBUM_THUMBS.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / year).mkdir(parents=True, exist_ok=True)

    images_data = []
    if ALBUM_JSON.exists():
        with open(ALBUM_JSON, "r", encoding="utf-8") as f:
            images_data = json.load(f)

    already_processed = {item.get("source_file", "") for item in images_data}

    def get_next_idx(data):
        existing = [int(i['file'].split('_')[1].split('.')[0]) for i in data if 'photo_' in i['file']]
        return max(existing, default=0) + 1

    files = sorted([f for f in INCOMING_DIR.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS])
    if not files:
        return print("No images in /incoming")

    any_remaining = False

    for img_path in files:
        img_path = sanitize_filename(img_path)

        if img_path.name in already_processed:
            print(f"⏭️  Skipping {img_path.name} (already processed)")
            continue

        idx = get_next_idx(images_data)
        new_name = f"photo_{idx:03d}.jpg"
        print(f"Processing {img_path.name}...")

        try:
            with Image.open(img_path) as img:
                img = ImageOps.exif_transpose(img)
                w, h = img.size

                # --- Thumbnail (local, saved to disk) ---
                thumb = img.copy()
                thumb.thumbnail(THUMB_MAX_SIZE)
                thumb.convert("RGB").save(ALBUM_THUMBS / new_name, "JPEG", quality=85)

                # --- Web version (1800px, uploaded to imgbb for lightbox) ---
                web = img.copy()
                web.thumbnail(WEB_MAX_SIZE)
                web_bytes = io.BytesIO()
                web.convert("RGB").save(web_bytes, "JPEG", quality=85)
                web_bytes = web_bytes.getvalue()

                # --- Full original (uploaded to imgbb for download button) ---
                with open(img_path, "rb") as f:
                    full_bytes = f.read()

        except Exception as e:
            print(f"  ❌ Failed to open image {img_path.name}: {e}")
            continue

        # Upload web version first
        print(f"  ↑ Uploading web version...")
        web_url = upload_to_imgbb(web_bytes)
        if not web_url:
            print(f"  ❌ Web upload failed for {img_path.name} — skipping.")
            (ALBUM_THUMBS / new_name).unlink(missing_ok=True)
            any_remaining = True
            continue

        # Upload full original
        print(f"  ↑ Uploading full version...")
        full_url = upload_to_imgbb(full_bytes)
        if not full_url:
            print(f"  ❌ Full upload failed for {img_path.name} — skipping.")
            (ALBUM_THUMBS / new_name).unlink(missing_ok=True)
            any_remaining = True
            continue

        images_data.append({
            "file": new_name,
            "source_file": img_path.name,
            "web_url": web_url,
            "full_url": full_url,
            "width": w,
            "height": h
        })

        # Save after every successful upload so progress is never lost
        with open(ALBUM_JSON, "w", encoding="utf-8") as f:
            json.dump(images_data, f, indent=2)

        img_path.unlink()
        print(f"  ✅ {new_name}")

    if not any_remaining:
        images_data = strip_source_fields(images_data, ALBUM_JSON)
        print(f"\n✅ Done. {len(images_data)} photos in album.")
    else:
        print(f"\n⚠️  Some images failed. Fix them and re-run to finish.")
        print(f"   source_file fields kept in JSON to allow safe restart.")

if __name__ == "__main__":
    print("--- Gallery Manager ---")
    print("[1] Add new photos")
    print("[2] Rename an album")
    print("[3] Just refresh menu")
    choice = input("\nChoose option: ").strip()
    if choice == "1":
        process_images()
        rebuild_master_files()
    elif choice == "2":
        rename_album()
        rebuild_master_files()
    elif choice == "3":
        rebuild_master_files()
