import json
from pathlib import Path

# ---------------- CONFIG ----------------
BASE_DIR = Path(__file__).parent.parent
IMAGE_ROOT = BASE_DIR / "images"
DATA_DIR = BASE_DIR / "data"
# ----------------------------------------

def select_from_options(options, prompt):
    print(f"\nAvailable {prompt}s:")
    for i, opt in enumerate(options, 1):
        print(f"[{i}] {opt}")
    choice = int(input(f"Select {prompt} (number): ")) - 1
    return options[choice]

def reindex_album(images_data, ALBUM_THUMBS, ALBUM_JSON):
    """Renames all thumbnails sequentially using a two-pass approach."""
    print("\n🔄 Re-indexing all images...")

    # Pass 1: rename all thumbs to temp names based on their current filename
    temp_map = []
    for item in images_data:
        old_file = item['file']
        temp_name = f"_tmp_{old_file}"
        (ALBUM_THUMBS / old_file).rename(ALBUM_THUMBS / temp_name)
        temp_map.append((temp_name, item))

    # Pass 2: rename from temp to final sequential names
    new_data = []
    for idx, (temp_name, item) in enumerate(temp_map, 1):
        new_name = f"photo_{idx:03d}.jpg"
        (ALBUM_THUMBS / temp_name).rename(ALBUM_THUMBS / new_name)
        item['file'] = new_name
        new_data.append(item)
        print(f"  Item {idx}: -> {new_name}")

    with open(ALBUM_JSON, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2)

    return new_data

def run_swap():
    years = sorted([d.name for d in IMAGE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)
    if not years: return
    year = select_from_options(years, "Year")

    album_options = sorted([d.name for d in (IMAGE_ROOT / year).iterdir() if d.is_dir()])
    if not album_options: return
    album_slug = select_from_options(album_options, "Album")

    ALBUM_JSON = DATA_DIR / year / f"{album_slug}.json"
    ALBUM_THUMBS = IMAGE_ROOT / year / album_slug / "thumbs"

    with open(ALBUM_JSON, "r", encoding="utf-8") as f:
        images_data = json.load(f)

    print(f"\nCurrently {len(images_data)} images in {album_slug}")

    val1 = input("\nFirst photo number to swap (e.g. 1): ").strip().zfill(3)
    val2 = input("Second photo number to swap (e.g. 5): ").strip().zfill(3)

    def get_item(num):
        return next(((i, x) for i, x in enumerate(images_data) if f"_{num}." in x['file']), (None, None))

    idx1, item1 = get_item(val1)
    idx2, item2 = get_item(val2)

    if item1 and item2:
        images_data[idx1], images_data[idx2] = images_data[idx2], images_data[idx1]
        reindex_album(images_data, ALBUM_THUMBS, ALBUM_JSON)
        print(f"\n✅ Swap and re-index successful.")
    else:
        print("❌ One or both numbers not found.")

if __name__ == "__main__":
    run_swap()
