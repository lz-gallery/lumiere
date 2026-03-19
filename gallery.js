let lightbox;

// ─── CONFIG ──────────────────────────────────────────────────────────────────
//
//  Set to '' when testing locally (http://127.0.0.1:5500/)
//  Set to '/lumiere' before pushing to GitHub Pages
//
const BASE_PATH = '/lumiere';
//
// ─────────────────────────────────────────────────────────────────────────────

// Helper — builds an absolute path from the repo root so fetch()
// always resolves correctly regardless of what the current URL looks like.
function rootPath(path) {
    return `${BASE_PATH}/${path}`.replace('//', '/');
}

// ─── URL ROUTING ────────────────────────────────────────────────────────────

function routeFromURL() {
    const params = new URLSearchParams(window.location.search);
    const redirected = params.get('p');
    if (redirected) {
        window.history.replaceState({}, '', redirected);
    }

    const rawPath = redirected || window.location.pathname;

    const path = rawPath
        .replace(new RegExp('^' + BASE_PATH), '')
        .replace(/^\/|\/$/g, '');

    const parts = path.split('/').filter(Boolean);

    if (parts.length === 0) {
        showHome(false);
    } else if (parts.length === 1) {
        loadYearView(parts[0], false);
    } else if (parts.length === 2) {
        loadAlbum(`data/${parts[0]}/${parts[1]}.json`, false);
    } else {
        showHome(false);
    }
}

window.addEventListener('popstate', () => {
    routeFromURL();
});

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        routeFromURL();
    }
});

// ─── MENU ────────────────────────────────────────────────────────────────────

function toggleYear(yearId, forceState) {
    const element = document.getElementById(yearId);
    if (!element) return;

    document.querySelectorAll('.menu-albums').forEach(el => {
        if (el.id !== yearId) el.style.display = 'none';
    });

    if (forceState === 'open') {
        element.style.display = 'block';
    } else if (forceState === 'close') {
        element.style.display = 'none';
    } else {
        element.style.display = element.style.display === 'block' ? 'none' : 'block';
    }
}

function loadMenu() {
    fetch(rootPath('menu.html'))
        .then(response => response.text())
        .then(data => {
            const menuContainer = document.getElementById('album-menu');
            menuContainer.innerHTML = data;
            menuContainer.querySelectorAll('div').forEach(el => {
                if (el.getAttribute('onclick')?.includes('toggleYear')) {
                    el.classList.add('menu-year');
                }
            });
        })
        .catch(err => console.error("Menu failed to load:", err));
}

// ─── HOME SCREEN ─────────────────────────────────────────────────────────────

async function showHome(push = true) {
    if (push) {
        window.history.pushState({}, '', BASE_PATH + '/');
    }

    const homeScreen = document.getElementById('home-screen');
    const galleryView = document.getElementById('gallery-view');

    document.querySelectorAll('.menu-albums').forEach(el => el.style.display = 'none');

    homeScreen.style.display = 'grid';
    homeScreen.style.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))';
    homeScreen.style.gap = '20px';
    galleryView.style.display = 'none';
    homeScreen.innerHTML = '<p>Loading...</p>';

    try {
        const response = await fetch(rootPath('data/albums_list.json'));
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const structure = await response.json();
        homeScreen.innerHTML = '';

        const years = Object.keys(structure).sort((a, b) => b - a);

        for (const year of years) {
            const albumsInYear = structure[year];
            if (albumsInYear.length === 0) continue;

            const firstAlbum = albumsInYear[0];
            const albRes = await fetch(rootPath(firstAlbum.file));
            const images = await albRes.json();

            const slug = firstAlbum.file.split('/').pop().replace('.json', '');
            const thumbPath = rootPath(`images/${year}/${slug}/thumbs/${images[0].file}`);

            const card = document.createElement('div');
            card.className = 'album-card';
            card.onclick = () => loadYearView(year);

            card.innerHTML = `
                <img src="${thumbPath}" loading="lazy">
                <div class="album-info">
                    <h2>${year}</h2>
                    <span>${albumsInYear.length} Albums</span>
                </div>
            `;
            homeScreen.appendChild(card);
        }
    } catch (e) {
        console.error('Error loading home:', e);
        homeScreen.innerHTML = `<p>Error loading: ${e.message}</p>`;
    }
}

// ─── YEAR VIEW ───────────────────────────────────────────────────────────────

async function loadYearView(year, push = true) {
    if (push) {
        window.history.pushState({}, '', `${BASE_PATH}/${year}`);
    }

    const homeScreen = document.getElementById('home-screen');
    const galleryView = document.getElementById('gallery-view');

    homeScreen.style.display = 'grid';
    homeScreen.style.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))';
    homeScreen.style.gap = '20px';
    galleryView.style.display = 'none';

    toggleYear(`year-${year}`, 'close');

    homeScreen.innerHTML = `
        <h1 class="view-title">
            <span class="back-arrow" onclick="showHome()" title="Back to Home">←</span>
            ${year}
        </h1>
    `;

    try {
        const response = await fetch(rootPath('data/albums_list.json'));
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const structure = await response.json();
        const albums = structure[year];

        for (const album of albums) {
            const albRes = await fetch(rootPath(album.file));
            const images = await albRes.json();
            const albumSlug = album.file.split('/').pop().replace('.json', '');

            const card = document.createElement('div');
            card.className = 'album-card';
            card.onclick = () => loadAlbum(album.file);

            card.innerHTML = `
                <img src="${rootPath(`images/${year}/${albumSlug}/thumbs/${images[0].file}`)}" loading="lazy">
                <div class="album-info">
                    <h2>${album.title.toUpperCase()}</h2>
                    <span>${images.length} Photos</span>
                </div>
            `;
            homeScreen.appendChild(card);
        }
    } catch (err) {
        console.error('Error loading year:', err);
        homeScreen.innerHTML += `<p>Error loading albums: ${err.message}</p>`;
    }
}

// ─── ALBUM / PHOTO VIEW ──────────────────────────────────────────────────────

function loadAlbum(jsonPath, push = true) {
    const homeScreen = document.getElementById('home-screen');
    const galleryView = document.getElementById('gallery-view');

    homeScreen.style.display = 'none';
    galleryView.style.display = 'block';

    const gallery = document.getElementById('gallery');
    const title = document.getElementById('album-title');
    gallery.innerHTML = 'Loading photos...';

    const parts = jsonPath.split('/');
    const year = parts[1];
    const slug = parts[2].replace('.json', '');

    if (push) {
        window.history.pushState({}, '', `${BASE_PATH}/${year}/${slug}`);
    }

    title.innerHTML = `
        <span class="back-arrow" onclick="loadYearView('${year}')" title="Back to ${year}">←</span>
        ${slug.toUpperCase().replace(/_/g, ' ')}
    `;

    toggleYear(`year-${year}`, 'open');

    fetch(rootPath(`data/${year}/${slug}.json`) + `?v=${new Date().getTime()}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(images => {
            gallery.innerHTML = '';
            images.forEach(img => {
                const link = document.createElement('a');
                link.href = img.full_url;
                link.dataset.pswpWidth = img.width;
                link.dataset.pswpHeight = img.height;
                link.target = "_blank";
                link.rel = "noopener noreferrer";

                const image = document.createElement('img');
                image.src = rootPath(`images/${year}/${slug}/thumbs/${img.file}`);
                image.loading = 'lazy';
                link.appendChild(image);
                gallery.appendChild(link);
            });

            if (lightbox) lightbox.destroy();
            if (typeof PhotoSwipeLightbox !== 'undefined') {
                lightbox = new PhotoSwipeLightbox({
                    gallery: '#gallery',
                    children: 'a',
                    pswpModule: PhotoSwipe,
                    wheelToZoom: true
                });

                lightbox.on('uiRegister', function() {
                    lightbox.pswp.ui.registerElement({
                        name: 'download-button',
                        order: 8,
                        isButton: true,
                        tagName: 'a',
                        html: {
                            isCustomSVG: true,
                            inner: '<path d="M20.5 14.3 17.1 18V10h-2.2v7.9l-3.4-3.6L10 16l6 6.1 6-6.1ZM23 23H9v2h14Z" id="pswp__icn-download"/>',
                            outlineID: 'pswp__icn-download'
                        },
                        onInit: (el, pswp) => {
                            el.setAttribute('download', '');
                            el.setAttribute('target', '_blank');
                            el.setAttribute('rel', 'noopener');

                            pswp.on('change', () => {
                                el.href = pswp.currSlide.data.element.href;
                            });
                        }
                    });
                });

                lightbox.init();
            }
        })
        .catch(err => {
            console.error('Error loading album:', err);
            gallery.innerHTML = `<p>Error loading photos: ${err.message}</p>`;
        });
}

// ─── INIT ─────────────────────────────────────────────────────────────────────

window.onload = () => {
    loadMenu();
    routeFromURL();
};
