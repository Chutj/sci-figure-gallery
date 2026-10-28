(() => {
  'use strict';
  const data = document.getElementById('gallery-data');
  if (!data) return;
  let raw;
  try { raw = JSON.parse(data.textContent); } catch { raw = []; }
  const candidateMode = data.dataset.mode === 'candidate';
  const publicMode = data.dataset.mode === 'public' || candidateMode;
  const publicHosts = (data.dataset.imageHosts || '').split(',').filter(Boolean);
  const tools = globalThis.GalleryTools;
  const safePath = value => {
    if (typeof value !== 'string') return '';
    if (!publicMode || candidateMode) return /^\/(?!\/)[^\\]*$/.test(value) ? value : '';
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && !url.username && !url.password && !url.search && !url.hash
        && publicHosts.includes(url.host) ? value : '';
    } catch { return ''; }
  };
  const figures = (Array.isArray(raw) ? raw : []).map(f => ({
    ...f, title: f.title || 'Untitled figure', primary: f.primary || 'Uncategorized',
    categories: Array.isArray(f.categories) ? f.categories.filter(v => typeof v === 'string') : [],
    sections: f.sections && typeof f.sections === 'object' ? f.sections : {},
    image: safePath(f.image), thumbnail: safePath(f.thumbnail),
    width: Number(f.width) > 0 ? Number(f.width) : 4,
    height: Number(f.height) > 0 ? Number(f.height) : 3,
  }));
  document.body.classList.add('gallery-page');
  const query = document.getElementById('gallery-query');
  const category = document.getElementById('gallery-category');
  const focus = document.getElementById('gallery-focus');
  const sort = document.getElementById('gallery-sort');
  const grid = document.getElementById('gallery-grid');
  const dialog = document.getElementById('figure-detail');
  const image = document.getElementById('detail-image');
  const viewport = document.getElementById('detail-viewport');
  const count = document.getElementById('gallery-count');
  const advancedPanel = document.getElementById('gallery-advanced');
  const advancedInputs = [...advancedPanel.querySelectorAll('[data-search-field]')];
  const paletteCache = new Map();
  let opener, activeFigure, zoom = 1, pendingLayout = 0;
  const text = (id, value) => { document.getElementById(id).textContent = value || ''; };
  const meta = figure => [figure.journal, figure.year, tools.formatFigureReference(figure.figure)].filter(Boolean).join(' · ') || 'Source information unavailable';
  const categories = [...new Set(figures.flatMap(f => tools.browsingCategories(f)))].sort();
  categories.forEach(name => {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = `${name} (${figures.filter(f => f.categories.includes(name)).length})`;
    (tools.categoryGroup(name) === 'type' ? category : focus).append(option);
  });
  function layout() {
    pendingLayout = 0;
    const style = getComputedStyle(grid);
    const columns = Number(style.getPropertyValue('--gallery-columns')) || 1;
    const gap = Number.parseFloat(style.getPropertyValue('--gallery-gap')) || 12;
    const width = (grid.clientWidth - gap * (columns - 1)) / columns;
    if (width <= 0) return;
    const cards = [...grid.children];
    grid.classList.add('is-masonry');
    cards.forEach(card => { card.style.width = `${width}px`; });
    // DOM/tab order remains the sorted catalog order. Each next card starts at
    // the lowest available top position, leftmost column on ties.
    const heights = new Array(columns).fill(0);
    const measured = cards.map(card => card.getBoundingClientRect().height);
    cards.forEach((card, index) => {
      const column = heights.indexOf(Math.min(...heights));
      card.style.transform = `translate(${column * (width + gap)}px, ${heights[column]}px)`;
      heights[column] += measured[index] + gap;
    });
    grid.style.height = `${cards.length ? Math.max(...heights) - gap : 0}px`;
  }
  function scheduleLayout() {
    if (!pendingLayout) pendingLayout = requestAnimationFrame(layout);
  }
  const resizeObserver = typeof ResizeObserver === 'function' ? new ResizeObserver(scheduleLayout) : null;
  resizeObserver?.observe(grid);
  window.addEventListener('resize', scheduleLayout);
  document.fonts?.ready.then(scheduleLayout);
  function setZoom(value) {
    if (!activeFigure) return;
    zoom = Math.max(0.05, Math.min(4, value));
    image.style.width = `${activeFigure.width * zoom}px`;
    text('zoom-level', `${Math.round(zoom * 100)}%`);
  }
  function fitImage() {
    if (!activeFigure) return;
    setZoom(Math.min(1, (viewport.clientWidth - 2) / activeFigure.width,
      window.innerHeight * 0.65 / activeFigure.height));
    viewport.scrollTo(0, 0);
  }
  image.addEventListener('error', () => {
    image.hidden = true;
    text('zoom-level', 'Image unavailable');
    document.getElementById('detail-image-error').hidden = false;
    const caption = document.getElementById('detail-color-caption');
    if (caption && !tools.recordedColors(activeFigure || {}).length) caption.textContent = 'Color samples are unavailable for this image.';
  });
  function showPalette(colors, caption) {
    const palette = document.getElementById('detail-palette');
    if (!palette) return;
    palette.replaceChildren(); text('detail-color-caption', caption);
    const recorded = new Set(tools.recordedColors(activeFigure || {}));
    colors.forEach(hex => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'color-swatch';
      button.setAttribute('aria-label', `Copy color ${hex}`); button.title = `Copy ${hex}`;
      const chip = document.createElement('span'); chip.className = 'color-chip'; chip.style.backgroundColor = hex; chip.setAttribute('aria-hidden', 'true');
      const code = document.createElement('code'); code.textContent = hex;
      const source = document.createElement('span'); source.className = 'color-source';
      source.textContent = recorded.has(hex) ? 'From notes' : 'Sampled';
      button.append(chip, code, source); palette.append(button);
      button.addEventListener('click', async () => {
        try {
          if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
          await navigator.clipboard.writeText(hex);
          text('detail-color-status', `Copied ${hex}`);
        } catch {
          text('detail-color-status', `Copy is unavailable in this browser. Select this HEX value: ${hex}`);
        }
      });
    });
  }
  function updatePalette() {
    if (!activeFigure || !document.getElementById('detail-palette')) return;
    const recorded = tools.recordedColors(activeFigure);
    if (recorded.length) showPalette(recorded, 'HEX values recorded in the figure notes. Click a swatch to copy.');
    const key = `${activeFigure.id}|${activeFigure.image}`;
    const showSamples = colors => showPalette([...new Set([...recorded, ...colors])].slice(0, 8),
      colors.length ? 'Each color is labeled as recorded or sampled. Sampled values are approximate, not author-specified HEX values. Click a swatch to copy.'
      : recorded.length ? 'HEX values recorded in the figure notes. Click a swatch to copy.' : 'No distinct colors could be sampled from this image.');
    if (paletteCache.has(key)) { showSamples(paletteCache.get(key)); return; }
    if (!image.complete || !image.naturalWidth) return;
    try {
      const canvas = document.createElement('canvas');
      const ratio = Math.min(1, 220 / Math.max(image.naturalWidth, image.naturalHeight));
      canvas.width = Math.max(1, Math.round(image.naturalWidth * ratio));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * ratio));
      const context = canvas.getContext('2d', {willReadFrequently: true});
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const colors = tools.sampleColors(context.getImageData(0, 0, canvas.width, canvas.height).data);
      paletteCache.set(key, colors);
      showSamples(colors);
    } catch {
      showPalette(recorded, 'Image sampling is unavailable. Any displayed HEX values come from the figure notes.');
    }
  }
  image.addEventListener('load', updatePalette);
  function openFigure(figure, button) {
    opener = button; activeFigure = figure;
    text('detail-title', figure.title); text('detail-meta', meta(figure));
    const displayedCategories = tools.browsingCategories(figure);
    text('detail-categories', displayedCategories.length ? `Filed under: ${displayedCategories.join(' · ')}` : 'Category unavailable');
    text('detail-paper', figure.paper || 'Paper title unavailable');
    document.getElementById('detail-translation').hidden = publicMode;
    text('detail-translation', publicMode ? '' : !figure.translation_status || figure.translation_status === 'reviewed'
      ? 'English translation of the existing library notes.'
      : 'English translation pending review. Original notes are retained in the local inventory. Any PDF-based candidate below is a draft requiring human review.');
    text('detail-author', figure.author ? `${publicMode ? 'Authors' : 'First author'}: ${figure.author}` : 'Author information unavailable');
    const rights = document.getElementById('detail-rights');
    rights.hidden = !publicMode;
    rights.textContent = '';
    if (publicMode) {
      const r = figure.rights || {};
      [['Authors / Attribution', r.attribution], ['License Type and Version', r.license],
        ['Modification Status', r.modification_status], ['Additional Credit or Permission Notice', r.additional_credit]]
        .forEach(([label, value]) => {
          const p = document.createElement('span'); p.style.display = 'block';
          p.textContent = `${label}: ${value || 'Not recorded — publication review incomplete'}`;
          rights.append(p);
        });
    }
    if (publicMode && typeof figure.rights.license_url === 'string'
        && figure.rights.license_url.startsWith('https://')) {
      const license = document.createElement('a'); license.href = figure.rights.license_url;
      license.textContent = ' License terms'; license.target = '_blank'; license.rel = 'noopener';
      rights.append(license);
    }
    image.hidden = !figure.image;
    document.getElementById('detail-image-error').hidden = Boolean(figure.image);
    image.removeAttribute('src'); image.alt = figure.title;
    image.width = figure.width; image.height = figure.height;
    if (figure.image) image.src = figure.image;
    const original = document.getElementById('detail-original');
    original.hidden = !figure.image; original.removeAttribute('href');
    if (figure.image) original.href = figure.image;
    const doi = document.getElementById('detail-doi');
    doi.removeAttribute('href');
    const validDOI = typeof figure.doi === 'string' && /^10\.\d{4,9}\/\S+$/.test(figure.doi);
    doi.textContent = validDOI ? `DOI: ${figure.doi}` : 'DOI unavailable';
    if (validDOI) doi.href = `https://doi.org/${figure.doi}`;
    const notes = document.getElementById('detail-notes'); notes.replaceChildren();
    tools.sections.forEach(heading => {
      const section = document.createElement('section');
      const h3 = document.createElement('h3'); h3.textContent = heading;
      const p = document.createElement('p'); p.textContent = figure.sections[heading] || 'Not recorded in the source notes.';
      section.append(h3, p); notes.append(section);
      if (heading === 'Color & encoding') {
        const palette = document.createElement('div'); palette.id = 'detail-palette'; palette.className = 'figure-palette';
        palette.setAttribute('role', 'group'); palette.setAttribute('aria-label', 'Copy figure colors');
        const caption = document.createElement('p'); caption.id = 'detail-color-caption'; caption.className = 'gallery-muted';
        caption.textContent = 'Color samples appear when the figure finishes loading.';
        const status = document.createElement('p'); status.id = 'detail-color-status'; status.className = 'gallery-muted';
        status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
        section.append(palette, caption, status);
        const legend = figure.legend;
        const legendPath = legend && safePath(legend.image);
        if (legendPath) {
          const details = document.createElement('details'); details.className = 'figure-legend';
          const summary = document.createElement('summary'); summary.textContent = 'Shared source legend';
          const link = document.createElement('a'); link.href = legendPath; link.target = '_blank'; link.rel = 'noopener';
          const img = document.createElement('img'); img.alt = legend.label || 'Shared source legend';
          img.width = legend.width; img.height = legend.height; img.loading = 'lazy';
          const note = document.createElement('p'); note.className = 'gallery-muted'; note.textContent = 'Shown separately from the original panel excerpt. Open the legend for full size.';
          img.addEventListener('error', () => { img.hidden = true; note.textContent = 'Legend preview unavailable. Open the source legend in a new tab.'; });
          link.append(img); details.append(summary, link, note); section.append(details);
          details.addEventListener('toggle', () => { if (details.open && !img.hasAttribute('src')) img.src = legendPath; });
        }
      }
    });
    if (!publicMode && figure.pdf_reference) {
      const ref = figure.pdf_reference;
      const section = document.createElement('section');
      const heading = document.createElement('h3'); heading.textContent = 'Local PDF evidence and review';
      const summary = document.createElement('p');
      summary.textContent = `${tools.formatFigureReference(ref.figure || figure.figure)} · PDF page ${ref.page || 'unresolved'} · Article license candidate: ${ref.article_license || 'unverified'} · Review: ${ref.review_status || 'unverified'}. No publication permission has been granted.`;
      section.append(heading, summary);
      if (ref.candidate_title) {
        const title = document.createElement('h3'); title.textContent = `English draft — ${ref.candidate_title}`;
        section.append(title);
      }
      tools.sections.forEach(label => {
        const value = (ref.candidate || {})[label];
        if (!value) return;
        const h = document.createElement('h4'); h.textContent = label;
        const p = document.createElement('p'); p.textContent = value;
        section.append(h, p);
      });
      notes.append(section);
    }
    dialog.showModal(); document.body.classList.add('gallery-modal-open');
    dialog.scrollTop = 0; fitImage(); updatePalette();
  }
  function render() {
    const advanced = Object.fromEntries(advancedInputs.map(input => [input.dataset.searchField, input.value]));
    const active = advancedInputs.filter(input => input.value.trim()).length;
    text('gallery-advanced-active', active ? ` · ${active} active` : '');
    const matches = figures.filter(figure => tools.matches(figure, query.value, category.value, advanced, focus.value));
    if (sort.value === 'title') matches.sort((a, b) => a.title.localeCompare(b.title, 'en'));
    if (sort.value === 'newest') matches.sort((a, b) => (Number(b.year) || 0) - (Number(a.year) || 0) || a.title.localeCompare(b.title, 'en'));
    [...grid.children].forEach(card => resizeObserver?.unobserve(card));
    grid.replaceChildren();
    matches.forEach(figure => {
      const article = document.createElement('article'); article.className = 'figure-card';
      const button = document.createElement('button'); button.type = 'button';
      button.setAttribute('aria-label', `View figure: ${figure.title}`);
      const unavailable = document.createElement('span'); unavailable.className = 'figure-image-missing';
      unavailable.textContent = 'Image unavailable'; unavailable.hidden = Boolean(figure.thumbnail);
      const img = document.createElement('img'); img.alt = ''; img.loading = 'lazy'; img.decoding = 'async';
      img.width = figure.width; img.height = figure.height;
      img.style.aspectRatio = `${figure.width} / ${figure.height}`;
      img.style.objectFit = 'contain';
      img.hidden = !figure.thumbnail;
      img.addEventListener('error', () => { img.hidden = true; unavailable.hidden = false; scheduleLayout(); }, { once: true });
      img.addEventListener('load', scheduleLayout, { once: true });
      if (figure.thumbnail) {
        if (figure.srcset && figure.srcset.split(',').every(part => safePath(part.trim().split(/\s+/)[0]))) img.srcset = figure.srcset;
        img.sizes = '(min-width: 1230px) 380px, (min-width: 1100px) 31vw, (min-width: 360px) 46vw, 92vw';
        img.src = figure.thumbnail;
      }
      const body = document.createElement('div'); body.className = 'figure-card-body';
      const label = document.createElement('span'); label.className = 'figure-category'; label.textContent = figure.primary;
      const title = document.createElement('h2'); title.textContent = figure.title;
      const source = document.createElement('p'); source.textContent = meta(figure);
      body.append(label, title, source); button.append(img, unavailable, body); article.append(button); grid.append(article);
      resizeObserver?.observe(article);
      button.addEventListener('click', () => openFigure(figure, button));
    });
    count.textContent = `${matches.length} of ${figures.length} figures${count.dataset.permissionNote || ''}`;
    document.getElementById('gallery-empty').hidden = matches.length > 0;
    layout();
  }
  query.addEventListener('input', render); category.addEventListener('change', render); focus.addEventListener('change', render); sort.addEventListener('change', render);
  advancedInputs.forEach(input => input.addEventListener('input', render));
  document.getElementById('gallery-reset').addEventListener('click', () => {
    query.value = ''; category.value = ''; focus.value = ''; sort.value = 'library';
    advancedInputs.forEach(input => { input.value = ''; }); advancedPanel.open = false;
    render(); query.focus();
  });
  document.getElementById('zoom-fit').addEventListener('click', fitImage);
  document.getElementById('zoom-actual').addEventListener('click', () => setZoom(1));
  document.getElementById('zoom-out').addEventListener('click', () => setZoom(zoom / 1.5));
  document.getElementById('zoom-in').addEventListener('click', () => setZoom(zoom * 1.5));
  dialog.addEventListener('keydown', e => {
    if (e.key === '+' || e.key === '=') { e.preventDefault(); setZoom(zoom * 1.5); }
    if (e.key === '-') { e.preventDefault(); setZoom(zoom / 1.5); }
    if (e.key === '0') { e.preventDefault(); fitImage(); }
    if (e.key === '1') { e.preventDefault(); setZoom(1); }
  });
  document.getElementById('detail-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) dialog.close();
  }});
  dialog.addEventListener('close', () => {
    document.body.classList.remove('gallery-modal-open');
    // Do not leave a full-resolution src active on the overview page.
    image.removeAttribute('src'); activeFigure = null;
    if (opener?.isConnected) opener.focus();
  });
  window.addEventListener('resize', () => { if (dialog.open) fitImage(); });
  render();
})();
