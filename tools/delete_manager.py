import json
import shutil
from pathlib import Path

# ---------------- CONFIG ----------------
BASE_DIR = Path(__file__).parent.parent
IMAGE_ROOT = BASE_DIR / "images"
DATA_DIR = BASE_DIR / "data"
# ----------------------------------------

def select_from_options(options, prompt):
    """Generates a numbered list in the terminal for selection."""
    print(f"\nAvailable {prompt}s:")
    for i, opt in enumerate(options, 1):
        print(f"[{i}] {opt}")
    choice = int(input(f"Select {prompt} (number): ")) - 1
    return options[choice]

def get_year_and_album():
    years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
    if not years:
        print("No year folders found.")
        return None, None
    year = select_from_options(years, "Year")

    album_options = sorted([d.name for d in (IMAGE_ROOT / year).iterdir() if d.is_dir()])
    if not album_options:
        print(f"No albums found in {year}.")
        return year, None
    album_slug = select_from_options(album_options, "Album")

    return year, album_slug

def delete_images():
    year, album_slug = get_year_and_album()
    if not album_slug: return

    ALBUM_JSON = DATA_DIR / year / f"{album_slug}.json"
    ALBUM_DIR = IMAGE_ROOT / year / album_slug
    ALBUM_THUMBS = ALBUM_DIR / "thumbs"

    if not ALBUM_JSON.exists():
        print(f"❌ Error: Album '{album_slug}' JSON not found in {year}.")
        return

    with open(ALBUM_JSON, "r", encoding="utf-8") as f:
        images_data = json.load(f)

    user_input = input("Which photo number(s) to delete? (e.g., 5, 9): ")
    targets = [id.strip().zfill(3) for id in user_input.replace(",", " ").split()]

    new_data = []
    for item in images_data:
        file_num = item["file"].split("_")[1].split(".")[0]
        if file_num in targets:
            (ALBUM_THUMBS / item["file"]).unlink(missing_ok=True)
            print(f"🗑️  Deleted {item['file']} from local thumbs and JSON.")
        else:
            new_data.append(item)

    with open(ALBUM_JSON, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2)
    print("✅ Image deletion complete.")

def delete_album():
    year, album_slug = get_year_and_album()
    if not album_slug: return

    confirm = input(f"⚠️  ARE YOU SURE? This deletes the folder '{album_slug}' and its JSON. (y/n): ")
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
        print("🚀 Album fully removed. Please run prepare_album.py option 3 to refresh the menu.")
    except Exception as e:
        print(f"❌ Error during deletion: {e}")

if __name__ == "__main__":
    print("--- Gallery Deletion Manager ---")
    print("[1] Delete specific images from an album")
    print("[2] Delete an ENTIRE album")

    choice = input("\nChoose option: ").strip()
    if choice == "1":
        delete_images()
    elif choice == "2":
        delete_album()
    else:
        print("Invalid choice.")
