# Lumiere

A personal photo gallery built with vanilla HTML, CSS, and JavaScript, hosted on GitHub Pages. Photos are organized by year and album. Full-resolution images are hosted on [imgbb](https://imgbb.com/); thumbnails are stored in the repository.

---

## How It Works

The gallery has three levels of navigation:

```
Home (years) → Year view (albums) → Album view (photos)
```

Each level has its own URL, so albums can be shared as direct links:

```
https://lz-gallery.github.io/lumiere/              ← Home
https://lz-gallery.github.io/lumiere/2025          ← Year
https://lz-gallery.github.io/lumiere/2025/porto    ← Album
```

The browser back button works correctly at every level.

---

## File Structure

```
lumiere/
│
├── index.html                  # The single HTML page
├── gallery.js                  # All navigation and rendering logic
├── style.css                   # All styles
├── menu.html                   # Auto-generated navigation menu (do not edit manually)
├── 404.html                    # Handles direct URL visits on GitHub Pages
│
├── photoswipe.css              # PhotoSwipe lightbox styles
├── photoswipe-lightbox.umd.min.js
├── photoswipe.umd.min.js
│
├── data/
│   ├── albums_list.json        # Master index of all years and albums
│   └── 2025/
│       └── porto.json          # Photo list for each album
│
├── images/
│   └── 2025/
│       └── porto/
│           └── thumbs/         # Local thumbnails (max 600×600px)
│               ├── photo_001.jpg
│               └── ...
│
└── tools/
    ├── prepare_album.py        # Add new photos to an album
    ├── delete_manager.py       # Delete photos or entire albums (IS A PAIN IN THE A** TO USE)
    └── swap_images.py          # Reorder photos within an album (DOESN'T WORK)
```

Each album JSON file contains an array of photo entries:

```json
[
  {
    "file": "photo_001.jpg",
    "full_url": "https://i.ibb.co/...",
    "width": 3000,
    "height": 4000
  }
]
```

- `file` — the thumbnail filename, stored locally under `images/year/album/thumbs/`
- `full_url` — the full-resolution image hosted on imgbb, used by the lightbox
- `width` / `height` — original image dimensions, required by PhotoSwipe

---

## First-Time Setup

1. Get a free imgbb API key at [imgbb.com](https://imgbb.com/) (sign up → API)
2. Open `tools/prepare_album.py` and replace `YOUR_IMGBB_API_KEY_HERE` with your key
3. Install Python dependencies:
   ```bash
   pip install Pillow requests
   ```

---

## Adding New Photos

1. Drop your photos into the `incoming/` folder at the repo root
2. Run the tool:
   ```bash
   cd tools
   python prepare_album.py
   ```
3. Select or create a year and album when prompted
4. The script will:
   - Generate thumbnails and save them to `images/year/album/thumbs/`
   - Upload the full-resolution originals to imgbb
   - Update the album's JSON file
   - Rebuild `menu.html` and `data/albums_list.json`
5. Commit and push the changes to GitHub

---

## Deleting Photos or Albums

```bash
cd tools
python delete_manager.py
```

- Option `1` — delete specific photos from an album by number
- Option `2` — delete an entire album and all its files

After deleting, run `prepare_album.py` option `3` to rebuild the menu.

---

## Reordering Photos

```bash
cd tools
python swap_images.py
```

Select a year and album, then enter two photo numbers to swap their positions. The script re-indexes all filenames sequentially after the swap.

---

## Local Development

### Setting Up Live Server for SPA Routing

Install the [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) extension for VS Code, then create `.vscode/settings.json` with:

```json
{
    "liveServer.settings.file": "/index.html"
}
```

### BASE_PATH Setting

At the top of `gallery.js` there is a single config variable:

```javascript
const BASE_PATH = '';             // ← local development
const BASE_PATH = '/lumiere';     // ← GitHub Pages (production)
```

**Always set `BASE_PATH = ''` when developing locally, and set it back to `'/lumiere'` before pushing to GitHub.**

### Workflow

1. Set `BASE_PATH = ''` in `gallery.js`
2. Open the project in VS Code and click **Go Live**
3. Navigate to `http://127.0.0.1:5500/`
4. Make your changes and test
5. Set `BASE_PATH = '/lumiere'` in `gallery.js`
6. Commit and push

---

## Deployment

This project is hosted on **GitHub Pages** from the `main` branch. Every push to `main` automatically updates the live site at:

```
https://lz-gallery.github.io/lumiere/
```

Go to the repo **Settings → Pages** and set the source to the `main` branch if it isn't already.

No build step is required — everything is plain HTML, CSS, and JavaScript.

---

## Dependencies

| Library | Version | Purpose |
|---|---|---|
| [PhotoSwipe](https://photoswipe.com/) | 5.4.4 | Lightbox / fullscreen photo viewer |
| [imgbb](https://imgbb.com/) | — | Full-resolution image hosting |

All JavaScript dependencies are bundled locally — no CDN, no npm, no build tools required.
