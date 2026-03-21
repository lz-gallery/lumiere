let lightbox;

// ─── CONFIG ──────────────────────────────────────────────────────────────────
//
//  Set to '' when testing locally (http://127.0.0.1:5500/)
//  Set to '/lumiere' before pushing to GitHub Pages
//
const BASE_PATH = '/lumiere';
//
// ─────────────────────────────────────────────────────────────────────────────

function rootPath(path) {
    return `${BASE_PATH}/${path}`.replace('//', '/');
}

// ─── THEME ───────────────────────────────────────────────────────────────────

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('gallery-theme', newTheme);
    updateThemeToggle(newTheme);
}

function updateThemeToggle(theme) {
    const label = document.querySelector('.theme-label');
    if (label) label.textContent = theme === 'dark' ? 'DARK' : 'LIGHT';
}

function initTheme() {
    const saved = localStorage.getItem('gallery-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeToggle(saved);
}

// ─── ACTIVE STATES ───────────────────────────────────────────────────────────

function setActiveYear(year) {
    document.querySelectorAll('.menu-year').forEach(el => {
        el.classList.toggle('active', el.dataset.year === String(year));
    });
    const homeLink = document.querySelector('.nav-home');
    if (homeLink) homeLink.classList.toggle('active', !year);
}

function setActiveAlbum(slug) {
    document.querySelectorAll('.menu-albums a').forEach(el => {
        el.classList.toggle('active', Boolean(slug) && el.dataset.slug === slug);
    });
}

// ─── SVG BACK ARROW ──────────────────────────────────────────────────────────

function backArrowSVG() {
    return `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <polyline points="15 18 9 12 15 6"/>
    </svg>`;
}

// ─── CAPITALIZE HELPER ───────────────────────────────────────────────────────

function toTitleCase(str) {
    return str.replace(/_/g, ' ').replace(/\w\S*/g, w =>
        w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
    );
}

// ─── COVER HELPERS ───────────────────────────────────────────────────────────

// Returns the thumbnail filename to use for an album card
// Uses album.cover if set, otherwise falls back to images[0].file
function getAlbumCoverFile(album, images) {
    if (album.cover) {
        return `photo_${String(album.cover).padStart(3, '0')}.jpg`;
    }
    return images[0].file;
}

// Returns {albumSlug, coverFile} for a year card
// Uses year_cover_album/year_cover_photo if set on first album entry
function getYearCover(yearAlbums, year) {
    const first = yearAlbums[0];
    if (first.year_cover_album && first.year_cover_photo) {
        return {
            slug: first.year_cover_album,
            file: `photo_${String(first.year_cover_photo).padStart(3, '0')}.jpg`
        };
    }
    // Default: first album's first photo
    return null;
}

// ─── URL ROUTING ─────────────────────────────────────────────────────────────

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

// ─── HORIZONTAL SCROLL ───────────────────────────────────────────────────────

function initHorizontalScroll() {
    const yearsRow = document.querySelector('.years-row');
    if (!yearsRow) return;

    yearsRow.addEventListener('wheel', e => {
        e.preventDefault();
        yearsRow.scrollLeft += e.deltaY + e.deltaX;
    }, { passive: false });

    let isDown = false;
    let startX;
    let scrollLeft;

    yearsRow.addEventListener('mousedown', e => {
        isDown = true;
        yearsRow.classList.add('grabbing');
        startX = e.pageX - yearsRow.offsetLeft;
        scrollLeft = yearsRow.scrollLeft;
    });

    window.addEventListener('mouseup', () => {
        isDown = false;
        yearsRow.classList.remove('grabbing');
    });

    yearsRow.addEventListener('mousemove', e => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - yearsRow.offsetLeft;
        const walk = (x - startX) * 1.5;
        yearsRow.scrollLeft = scrollLeft - walk;
    });
}

// ─── MENU ─────────────────────────────────────────────────────────────────────

function toggleYear(yearId, forceState) {
    const yearEl = document.getElementById(yearId);
    if (!yearEl) return;

    const yearNum = yearId.replace('year-', '');
    const btn = document.querySelector(`.menu-year[data-year="${yearNum}"]`);

    document.querySelectorAll('.menu-albums').forEach(el => {
        if (el.id !== yearId) {
            el.classList.remove('visible');
            const otherYear = el.id.replace('year-', '');
            const otherBtn = document.querySelector(`.menu-year[data-year="${otherYear}"]`);
            if (otherBtn) otherBtn.classList.remove('open');
        }
    });

    let shouldOpen;
    if (forceState === 'open') shouldOpen = true;
    else if (forceState === 'close') shouldOpen = false;
    else shouldOpen = !yearEl.classList.contains('visible');

    yearEl.classList.toggle('visible', shouldOpen);
    if (btn) btn.classList.toggle('open', shouldOpen);
}

function loadMenu() {
    fetch(rootPath('menu.html'))
        .then(response => response.text())
        .then(data => {
            const menuContainer = document.getElementById('album-menu');
            const temp = document.createElement('div');
            temp.innerHTML = data;

            const yearsRow = document.createElement('div');
            yearsRow.className = 'years-row';

            const dropdowns = [];

            Array.from(temp.children).forEach(node => {
                const tag = node.tagName?.toLowerCase();
                const onclick = node.getAttribute('onclick') || '';
                const id = node.id || '';
                const classes = node.className || '';

                if (tag === 'a' && onclick.includes('showHome')) return;

                if (onclick.includes('toggleYear')) {
                    const yearMatch = onclick.match(/'year-(\d+)'/);
                    const year = yearMatch?.[1];
                    if (!year) return;

                    const btn = document.createElement('div');
                    btn.className = 'menu-year';
                    btn.dataset.year = year;
                    btn.setAttribute('onclick', `toggleYear('year-${year}')`);
                    btn.innerHTML = `${year} <span class="triangle">▼</span>`;
                    yearsRow.appendChild(btn);

                } else if (id.startsWith('year-') || classes.includes('menu-albums')) {
                    node.querySelectorAll('a').forEach(a => {
                        const m = (a.getAttribute('onclick') || '')
                            .match(/loadAlbum\('data\/\d+\/(.+?)\.json'\)/);
                        if (m) a.dataset.slug = m[1];
                    });
                    node.style.removeProperty('display');
                    dropdowns.push(node);
                }
            });

            menuContainer.innerHTML = '';
            menuContainer.appendChild(yearsRow);
            dropdowns.forEach(d => menuContainer.appendChild(d));

            initHorizontalScroll();
        })
        .catch(err => console.error("Menu failed to load:", err));
}

// ─── HOME SCREEN ─────────────────────────────────────────────────────────────

async function showHome(push = true) {
    if (push) {
        window.history.pushState({}, '', BASE_PATH + '/');
    }

    setActiveYear(null);
    setActiveAlbum(null);

    document.querySelectorAll('.menu-albums').forEach(el => el.classList.remove('visible'));
    document.querySelectorAll('.menu-year').forEach(el => el.classList.remove('open'));

    const homeScreen = document.getElementById('home-screen');
    const galleryView = document.getElementById('gallery-view');

    homeScreen.style.display = 'grid';
    galleryView.style.display = 'none';
    homeScreen.innerHTML = '<p style="color: var(--text-muted); font-size:0.85rem; letter-spacing:0.1em;">Loading...</p>';

    try {
        const response = await fetch(rootPath('data/albums_list.json'));
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const structure = await response.json();
        homeScreen.innerHTML = '';

        const years = Object.keys(structure).sort((a, b) => b - a);

        for (const year of years) {
            const albumsInYear = structure[year];
            if (albumsInYear.length === 0) continue;

            // Determine which album and photo to use for the year card cover
            const yearCover = getYearCover(albumsInYear, year);
            let thumbPath;

            if (yearCover) {
                // Use the specified cover photo from the specified album
                thumbPath = rootPath(`images/${year}/${yearCover.slug}/thumbs/${yearCover.file}`);
            } else {
                // Default: first album's cover photo (or first photo)
                const firstAlbum = albumsInYear[0];
                const albRes = await fetch(rootPath(firstAlbum.file));
                const images = await albRes.json();
                const slug = firstAlbum.file.split('/').pop().replace('.json', '');
                const coverFile = getAlbumCoverFile(firstAlbum, images);
                thumbPath = rootPath(`images/${year}/${slug}/thumbs/${coverFile}`);
            }

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
        homeScreen.innerHTML = `<p style="color:var(--text-muted)">Error loading: ${e.message}</p>`;
    }
}

// ─── YEAR VIEW ────────────────────────────────────────────────────────────────

async function loadYearView(year, push = true) {
    if (push) {
        window.history.pushState({}, '', `${BASE_PATH}/${year}`);
    }

    setActiveYear(year);
    setActiveAlbum(null);
    toggleYear(`year-${year}`, 'close');

    const homeScreen = document.getElementById('home-screen');
    const galleryView = document.getElementById('gallery-view');

    homeScreen.style.display = 'grid';
    galleryView.style.display = 'none';

    homeScreen.innerHTML = `
        <h1 class="view-title">
            <span class="back-arrow" onclick="showHome()" title="Back to Home">${backArrowSVG()}</span>
            <span class="year-text">${year}</span>
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

            // Use cover photo if set, otherwise first photo
            const coverFile = getAlbumCoverFile(album, images);

            const card = document.createElement('div');
            card.className = 'album-card';
            card.onclick = () => loadAlbum(album.file);

            card.innerHTML = `
                <img src="${rootPath(`images/${year}/${albumSlug}/thumbs/${coverFile}`)}" loading="lazy">
                <div class="album-info">
                    <h2>${album.title}</h2>
                    <span>${images.length} Photos</span>
                </div>
            `;
            homeScreen.appendChild(card);
        }
    } catch (err) {
        console.error('Error loading year:', err);
        homeScreen.innerHTML += `<p style="color:var(--text-muted)">Error: ${err.message}</p>`;
    }
}

// ─── ALBUM / PHOTO VIEW ───────────────────────────────────────────────────────

function loadAlbum(jsonPath, push = true) {
    const homeScreen = document.getElementById('home-screen');
    const galleryView = document.getElementById('gallery-view');

    homeScreen.style.display = 'none';
    galleryView.style.display = 'block';

    const gallery = document.getElementById('gallery');
    const titleEl = document.getElementById('album-title');
    gallery.innerHTML = '';

    const parts = jsonPath.split('/');
    const year = parts[1];
    const slug = parts[2].replace('.json', '');

    if (push) {
        window.history.pushState({}, '', `${BASE_PATH}/${year}/${slug}`);
    }

    setActiveYear(year);
    setActiveAlbum(slug);
    toggleYear(`year-${year}`, 'open');

    titleEl.innerHTML = `
        <span class="back-arrow" onclick="loadYearView('${year}')" title="Back to ${year}">${backArrowSVG()}</span>
        <span class="title-text">${toTitleCase(slug)}</span>
    `;

    fetch(rootPath(`data/${year}/${slug}.json`) + `?v=${new Date().getTime()}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(images => {
            gallery.innerHTML = '';
            images.forEach(img => {
                const link = document.createElement('a');
                link.href = img.web_url || img.full_url;
                link.dataset.pswpWidth = img.width;
                link.dataset.pswpHeight = img.height;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.dataset.fullUrl = img.full_url;

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
                                const currentEl = pswp.currSlide.data.element;
                                el.href = currentEl.dataset.fullUrl || currentEl.href;
                            });
                        }
                    });
                });

                lightbox.init();
            }
        })
        .catch(err => {
            console.error('Error loading album:', err);
            gallery.innerHTML = `<p style="color:var(--text-muted)">Error loading photos: ${err.message}</p>`;
        });
}

// ─── INIT ─────────────────────────────────────────────────────────────────────

window.onload = () => {
    initTheme();
    loadMenu();
    routeFromURL();
};
