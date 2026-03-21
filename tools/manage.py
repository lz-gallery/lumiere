import json
import shutil
import base64
import re
import io
import webbrowser
import tempfile
import requests
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
# ----------------------------------------

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def select_from_options(options, prompt):
    print(f"\nAvailable {prompt}s:")
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    choice = input(f"Select {prompt} (number): ").strip()
    try:
        return options[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return None

def get_year_and_album():
    years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
    if not years:
        print("No year folders found.")
        return None, None
    year = select_from_options(years, "Year")
    if not year: return None, None

    album_options = sorted([d.name for d in (IMAGE_ROOT / year).iterdir() if d.is_dir()])
    if not album_options:
        print(f"No albums found in {year}.")
        return year, None
    album_slug = select_from_options(album_options, "Album")
    return year, album_slug

def load_album_json(year, album_slug):
    path = DATA_DIR / year / f"{album_slug}.json"
    if not path.exists():
        print(f"❌ JSON not found for {album_slug}.")
        return None, None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path

def load_albums_list():
    path = DATA_DIR / "albums_list.json"
    if not path.exists():
        return {}, path
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path

def save_album_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def reindex_album(images_data, ALBUM_THUMBS, ALBUM_JSON):
    """Re-indexes all thumbnails sequentially using a two-pass approach."""
    print("\n🔄 Re-indexing all images...")

    temp_map = []
    for item in images_data:
        old_file = item['file']
        temp_name = f"_tmp_{old_file}"
        thumb = ALBUM_THUMBS / old_file
        if thumb.exists():
            thumb.rename(ALBUM_THUMBS / temp_name)
        temp_map.append((temp_name, item))

    new_data = []
    for idx, (temp_name, item) in enumerate(temp_map, 1):
        new_name = f"photo_{idx:03d}.jpg"
        temp_thumb = ALBUM_THUMBS / temp_name
        if temp_thumb.exists():
            temp_thumb.rename(ALBUM_THUMBS / new_name)
        item['file'] = new_name
        new_data.append(item)
        print(f"  {idx:03d} → {new_name}")

    save_album_json(new_data, ALBUM_JSON)
    return new_data

def rebuild_master_files():
    print("\nRefreshing master files...")

    # Load existing albums_list to preserve any cover settings
    existing, _ = load_albums_list()
    # Build a lookup of existing cover values keyed by file path
    cover_lookup = {}
    for year_albums in existing.values():
        for album in year_albums:
            if "cover" in album:
                cover_lookup[album["file"]] = album["cover"]

    structure = {}
    for year_folder in sorted(IMAGE_ROOT.iterdir()):
        if year_folder.is_dir() and year_folder.name.isdigit():
            year = year_folder.name
            structure[year] = []
            for album_folder in sorted(year_folder.iterdir()):
                if album_folder.is_dir() and (album_folder / "thumbs").exists():
                    album_slug = album_folder.name
                    display_name = album_slug.replace('_', ' ').upper()
                    if "CHILDRENS RAILWAY" in display_name:
                        display_name = display_name.replace("CHILDRENS", "CHILDREN'S")
                    file_path = f"data/{year}/{album_slug}.json"
                    entry = {"title": display_name, "file": file_path}
                    # Preserve existing cover setting if present
                    if file_path in cover_lookup:
                        entry["cover"] = cover_lookup[file_path]
                    structure[year].append(entry)

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

# ─── PREVIEW ─────────────────────────────────────────────────────────────────

def show_preview(year, album_slug, images_data, current_cover=None):
    """Generates a numbered HTML thumbnail grid and opens it in the browser."""
    ALBUM_THUMBS = IMAGE_ROOT / year / album_slug / "thumbs"

    cards = ""
    for item in images_data:
        num = item['file'].split('_')[1].split('.')[0]
        thumb_path = ALBUM_THUMBS / item['file']
        is_cover = current_cover is not None and int(num) == int(current_cover)

        if thumb_path.exists():
            with open(thumb_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            img_src = f"data:image/jpeg;base64,{b64}"
        else:
            img_src = ""

        cover_badge = '<div class="cover-badge">COVER</div>' if is_cover else ''

        cards += f"""
        <div class="card{'  cover' if is_cover else ''}">
            <img src="{img_src}" alt="{item['file']}">
            <div class="num">{num}</div>
            {cover_badge}
        </div>"""

    title = f"{album_slug.replace('_', ' ').upper()} — {year}"
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ margin: 0; padding: 20px; background: #161616; color: #eee;
         font-family: system-ui, sans-serif; }}
  h1 {{ font-size: 1em; font-weight: normal; opacity: 0.6;
        margin: 0 0 20px 0; letter-spacing: 2px; text-transform: uppercase; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .card {{ position: relative; width: 160px; }}
  .card img {{ width: 160px; height: 120px; object-fit: cover;
               border-radius: 6px; display: block; background: #333; }}
  .card.cover img {{ outline: 2px solid #fff; outline-offset: -2px; }}
  .num {{ position: absolute; bottom: 6px; left: 6px;
          background: rgba(0,0,0,0.75); color: #fff;
          font-size: 13px; font-weight: bold; padding: 2px 7px;
          border-radius: 4px; letter-spacing: 1px; }}
  .cover-badge {{ position: absolute; top: 6px; right: 6px;
                  background: #fff; color: #000;
                  font-size: 10px; font-weight: bold; padding: 2px 6px;
                  border-radius: 3px; letter-spacing: 1px; }}
</style>
</head>
<body>
<h1>{title} &nbsp;·&nbsp; {len(images_data)} photos</h1>
<div class="grid">{cards}</div>
</body>
</html>"""

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()
    webbrowser.open(f"file://{tmp.name}")
    print(f"\n🖼️  Preview opened in browser. Use the numbers shown to identify photos.")

# ─── OPERATIONS ──────────────────────────────────────────────────────────────

def delete_photos():
    year, album_slug = get_year_and_album()
    if not album_slug: return

    images_data, ALBUM_JSON = load_album_json(year, album_slug)
    if images_data is None: return

    ALBUM_THUMBS = IMAGE_ROOT / year / album_slug / "thumbs"

    show_preview(year, album_slug, images_data)

    user_input = input("\nWhich photo number(s) to delete? (e.g. 5, 9 or 5-9): ").strip()

    targets = set()
    for part in user_input.replace(",", " ").split():
        if "-" in part:
            start, end = part.split("-")
            targets.update(str(n).zfill(3) for n in range(int(start), int(end) + 1))
        else:
            targets.add(part.strip().zfill(3))

    new_data = []
    deleted = 0
    for item in images_data:
        file_num = item["file"].split("_")[1].split(".")[0]
        if file_num in targets:
            (ALBUM_THUMBS / item["file"]).unlink(missing_ok=True)
            print(f"🗑️  Deleted {item['file']}")
            deleted += 1
        else:
            new_data.append(item)

    if deleted == 0:
        print("No matching photos found.")
        return

    reindex_album(new_data, ALBUM_THUMBS, ALBUM_JSON)
    rebuild_master_files()
    print(f"\n✅ Deleted {deleted} photo(s) and re-indexed album.")

def swap_photos():
    year, album_slug = get_year_and_album()
    if not album_slug: return

    images_data, ALBUM_JSON = load_album_json(year, album_slug)
    if images_data is None: return

    ALBUM_THUMBS = IMAGE_ROOT / year / album_slug / "thumbs"

    show_preview(year, album_slug, images_data)

    val1 = input("\nFirst photo number to swap (e.g. 1): ").strip().zfill(3)
    val2 = input("Second photo number to swap (e.g. 5): ").strip().zfill(3)

    def get_item(num):
        return next(((i, x) for i, x in enumerate(images_data) if f"_{num}." in x['file']), (None, None))

    idx1, item1 = get_item(val1)
    idx2, item2 = get_item(val2)

    if item1 is None or item2 is None:
        print("❌ One or both numbers not found.")
        return

    images_data[idx1], images_data[idx2] = images_data[idx2], images_data[idx1]
    reindex_album(images_data, ALBUM_THUMBS, ALBUM_JSON)
    print(f"\n✅ Swapped photos {val1} and {val2} and re-indexed.")

def delete_album():
    year, album_slug = get_year_and_album()
    if not album_slug: return

    confirm = input(f"\n⚠️  ARE YOU SURE? This permanently deletes '{album_slug}' and all its data. (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    ALBUM_DIR = IMAGE_ROOT / year / album_slug
    ALBUM_JSON = DATA_DIR / year / f"{album_slug}.json"

    try:
        if ALBUM_DIR.exists():
            shutil.rmtree(ALBUM_DIR)
            print(f"✅ Deleted folder: {ALBUM_DIR}")
        if ALBUM_JSON.exists():
            ALBUM_JSON.unlink()
            print(f"✅ Deleted data file: {ALBUM_JSON}")
        rebuild_master_files()
        print("✅ Album fully removed.")
    except Exception as e:
        print(f"❌ Error: {e}")

def rename_album():
    years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
    if not years: return
    year = select_from_options(years, "Year")
    if not year: return

    album_options = sorted([d.name for d in (IMAGE_ROOT / year).iterdir() if d.is_dir()])
    old_name = select_from_options(album_options, "Album")
    if not old_name: return

    new_input = input(f"\nEnter NEW name for '{old_name}': ").strip()
    new_slug = new_input.lower().replace(" ", "_").replace("'", "")

    shutil.move(str(IMAGE_ROOT / year / old_name), str(IMAGE_ROOT / year / new_slug))
    old_json = DATA_DIR / year / f"{old_name}.json"
    if old_json.exists():
        shutil.move(str(old_json), str(DATA_DIR / year / f"{new_slug}.json"))

    rebuild_master_files()
    print(f"✅ Renamed to '{new_slug}'")

def set_cover():
    """Set the cover photo for an album card, and optionally for the year card."""
    print("\nSet cover for:")
    print("  [1] An album card")
    print("  [2] A year card (home screen)")
    sub = input("\nChoose: ").strip()

    if sub == "1":
        year, album_slug = get_year_and_album()
        if not album_slug: return

        images_data, _ = load_album_json(year, album_slug)
        if images_data is None: return

        # Load current cover if set
        albums_list, albums_list_path = load_albums_list()
        current_cover = None
        for album in albums_list.get(year, []):
            if album["file"] == f"data/{year}/{album_slug}.json":
                current_cover = album.get("cover")
                break

        show_preview(year, album_slug, images_data, current_cover)

        print(f"\nCurrent cover: photo {'%03d' % current_cover if current_cover else '001 (default — first photo)'}")
        choice = input("Enter photo number for new cover (or press Enter to keep default): ").strip()

        # Update albums_list.json
        for album in albums_list.get(year, []):
            if album["file"] == f"data/{year}/{album_slug}.json":
                if choice:
                    album["cover"] = int(choice)
                    print(f"✅ Cover set to photo {int(choice):03d}")
                else:
                    album.pop("cover", None)
                    print("✅ Cover reset to default (first photo)")
                break

        with open(albums_list_path, "w", encoding="utf-8") as f:
            json.dump(albums_list, f, indent=2)

    elif sub == "2":
        years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
        year = select_from_options(years, "Year")
        if not year: return

        albums_list, albums_list_path = load_albums_list()
        year_albums = albums_list.get(year, [])
        if not year_albums:
            print("No albums found for this year.")
            return

        # Show which albums are available and their current cover status
        print(f"\nAvailable albums in {year}:")
        for i, album in enumerate(year_albums, 1):
            slug = album["file"].split('/')[-1].replace('.json', '')
            cover = album.get("cover", "default")
            print(f"  [{i}] {album['title']} (cover: photo {cover:03d})" if cover != "default" else f"  [{i}] {album['title']} (cover: default)")

        album_choice = input("\nSelect which album to pull the cover photo from (number): ").strip()
        try:
            selected_album = year_albums[int(album_choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice.")
            return

        album_slug = selected_album["file"].split('/')[-1].replace('.json', '')
        images_data, _ = load_album_json(year, album_slug)
        if images_data is None: return

        current_year_cover = albums_list.get(year, [{}])[0].get("year_cover")
        show_preview(year, album_slug, images_data)

        choice = input("\nEnter photo number for year card cover (or press Enter for default): ").strip()

        # Store year cover as {album_slug, photo_number} on the first album entry
        # (year-level cover is stored on the year's first album entry for simplicity)
        if choice:
            for album in albums_list.get(year, []):
                album.pop("year_cover_album", None)
                album.pop("year_cover_photo", None)
            year_albums[0]["year_cover_album"] = album_slug
            year_albums[0]["year_cover_photo"] = int(choice)
            print(f"✅ Year {year} card cover set to {album_slug} / photo {int(choice):03d}")
        else:
            for album in year_albums:
                album.pop("year_cover_album", None)
                album.pop("year_cover_photo", None)
            print(f"✅ Year {year} card cover reset to default")

        with open(albums_list_path, "w", encoding="utf-8") as f:
            json.dump(albums_list, f, indent=2)

    else:
        print("Invalid choice.")

def sanitize_filename(path):
    clean_name = re.sub(r'[^\w.\-]', '_', path.name)
    clean_name = re.sub(r'_+', '_', clean_name)
    new_path = path.parent / clean_name
    if new_path != path:
        path.rename(new_path)
        print(f"  📝 Renamed '{path.name}' → '{clean_name}'")
    return new_path

def upload_to_imgbb(image_bytes):
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
    cleaned = [{k: v for k, v in item.items() if k != "source_file"} for item in images_data]
    save_album_json(cleaned, ALBUM_JSON)
    return cleaned

def add_photos():
    years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
    year = select_from_options(years, "Year")
    if not year:
        year = input("New Year (e.g. 2026): ").strip()

    albums = sorted([d.name for d in (IMAGE_ROOT / year).iterdir() if d.is_dir()]) if (IMAGE_ROOT / year).exists() else []
    album_slug = select_from_options(albums, "Album") if albums else None
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

                thumb = img.copy()
                thumb.thumbnail(THUMB_MAX_SIZE)
                thumb.convert("RGB").save(ALBUM_THUMBS / new_name, "JPEG", quality=85)

                web = img.copy()
                web.thumbnail(WEB_MAX_SIZE)
                web_bytes = io.BytesIO()
                web.convert("RGB").save(web_bytes, "JPEG", quality=85)
                web_bytes = web_bytes.getvalue()

                with open(img_path, "rb") as f:
                    full_bytes = f.read()

        except Exception as e:
            print(f"  ❌ Failed to open {img_path.name}: {e}")
            continue

        print(f"  ↑ Uploading web version...")
        web_url = upload_to_imgbb(web_bytes)
        if not web_url:
            print(f"  ❌ Web upload failed — skipping.")
            (ALBUM_THUMBS / new_name).unlink(missing_ok=True)
            any_remaining = True
            continue

        print(f"  ↑ Uploading full version...")
        full_url = upload_to_imgbb(full_bytes)
        if not full_url:
            print(f"  ❌ Full upload failed — skipping.")
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

        save_album_json(images_data, ALBUM_JSON)
        img_path.unlink()
        print(f"  ✅ {new_name}")

    if not any_remaining:
        images_data = strip_source_fields(images_data, ALBUM_JSON)
        print(f"\n✅ Done. {len(images_data)} photos in album.")
    else:
        print(f"\n⚠️  Some images failed. Fix them and re-run to finish.")

    rebuild_master_files()

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n─── Gallery Manager ───────────────────────────────")
    print("  [1] Add new photos")
    print("  [2] Delete photos from an album")
    print("  [3] Delete an entire album")
    print("  [4] Swap / reorder photos")
    print("  [5] Rename an album")
    print("  [6] Refresh menu")
    print("  [7] Set cover photo")
    print("───────────────────────────────────────────────────")

    choice = input("\nChoose option: ").strip()

    if choice == "1":
        add_photos()
    elif choice == "2":
        delete_photos()
    elif choice == "3":
        delete_album()
    elif choice == "4":
        swap_photos()
    elif choice == "5":
        rename_album()
    elif choice == "6":
        rebuild_master_files()
    elif choice == "7":
        set_cover()
    else:
        print("Invalid choice.")
