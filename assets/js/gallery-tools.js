/* Shared pure helpers: no source mutation, network access or permission changes. */
((root, factory) => {
  const tools = factory();
  if (typeof module === 'object' && module.exports) module.exports = tools;
  else root.GalleryTools = tools;
})(globalThis, () => {
  'use strict';
  const sections = ['What the figure shows', 'Statistics & symbols', 'Color & encoding', 'Design lessons'];
  const universalCategories = new Set(['Color references', 'Legends, color scales & symbols']);
  const browsingCategories = figure => (figure.categories || []).filter(name => !universalCategories.has(name));
  // Browsing facets only: do not rewrite the reviewed source categories.
  const figureTypes = new Set(['Maps', 'Scatter plots', 'Lines, curves & time series',
    'Bar charts', 'Histograms', 'Composition charts', 'Polar plots',
    'Box, violin & raincloud plots', 'Heatmaps & matrices',
    'Density, ridgelines & cumulative distributions', 'Error bars, intervals & forest plots',
    'Bubble plots', 'Contours & response surfaces', 'Sankey & chord diagrams']);
  const categoryGroup = name => figureTypes.has(name) ? 'type' : 'focus';
  const terms = value => String(value || '').toLocaleLowerCase('en').trim().split(/\s+/).filter(Boolean);
  const contains = (value, query) => terms(query).every(term => String(value || '').toLocaleLowerCase('en').includes(term));
  // Presentation only: retain the reviewed source reference and its panel case.
  // Never infer panel letters from a journal name or a positional description.
  function formatFigureReference(value) {
    const original = String(value || '').trim();
    const match = original.match(/^fig(?:ure)?\.?\s*(\d+)(.*)$/i);
    if (!match) return original;
    const base = `Fig. ${match[1]}`;
    const suffix = match[2].trim().replace(/^[·:]\s*/, '').replace(/^\(\s*/, '').replace(/\s*\)$/, '');
    if (!suffix || /^(?:full\s+figure|complete|all)(?:\b|$)/i.test(suffix)) return base;
    const handles = new Set(['aims','bars','budget','changes','curves','density','distributions','histograms','importance','key','left','leftmaps','lower','lowermaps','map','map_callouts','maps','middle','photo','photos','plot','points','regional','rest','right','rightmaps','sections','series','stats','summary','trajectories','uppermaps','violin','violins']);
    if (handles.has(suffix.toLowerCase())) return base;
    const numbered = suffix.match(/^(?:[a-z]\d+){2,}$|^(?:[A-Z]\d+){2,}$/);
    if (numbered) return base + suffix.match(/[A-Za-z]\d+/g).join(',');
    if (/^(?:[a-z]{2,12}|[A-Z]{2,12})$/.test(suffix)) {
      const panels = [...suffix];
      if (panels.every((p, i) => i === 0 || p.charCodeAt(0) > panels[i - 1].charCodeAt(0))) {
        const runs = [];
        for (let i = 0; i < panels.length;) {
          let end = i;
          while (end + 1 < panels.length && panels[end + 1].charCodeAt(0) === panels[end].charCodeAt(0) + 1) end++;
          runs.push(i === end ? panels[i] : panels[i]+'–'+panels[end]);
          i = end + 1;
        }
        return base + runs.join(',');
      }
    }
    const letter = '[A-Za-z](?:\\s*[-–—−]\\s*[A-Za-z])?';
    const panels = suffix.match(new RegExp(`^(${letter}(?:\\s*(?:[, +&]\\s*)${letter})*)(?=$|[\\s_)])`));
    if (panels) {
      const compact = panels[1].replace(/\s+/g, '').replace(/[—−-]/g, '–').replace(/[+&]/g, ',');
      return base + compact;
    }
    // Known source-library descriptors are not part of the figure citation.
    if (/^(?:(?:left|right|top|bottom|central)\s+)?(?:maps?|regions?|region locator|global|area curve|ecosystem pies|box-plot panels)\b/i.test(suffix)) return base;
    // Preserve unfamiliar references rather than silently inventing a panel set.
    return original;
  }
  function fields(figure) {
    const notes = figure.sections || {};
    const draft = figure.pdf_reference?.candidate || {};
    return {
      title: [figure.title, figure.paper, figure.pdf_reference?.candidate_title].join(' '), author: figure.author,
      doi: figure.doi, journal: figure.journal, year: figure.year, figure: [figure.figure, formatFigureReference(figure.figure)].join(' '),
      color: [notes['Color & encoding'], draft['Color & encoding'], ...(figure.colors?.hex_values || [])].join(' '),
      method: [figure.title, ...browsingCategories(figure), ...sections.filter(s => s !== 'Color & encoding').flatMap(s => [notes[s], draft[s]])].join(' '),
    };
  }
  function matches(figure, query, category, advanced = {}, focus = '') {
    const values = fields(figure);
    if (category && !(figure.categories || []).includes(category)) return false;
    if (focus && !(figure.categories || []).includes(focus)) return false;
    if (!contains(Object.values(values).join(' '), query)) return false;
    return Object.entries(advanced).every(([key, value]) => {
      if (!String(value).trim()) return true;
      if (!Object.hasOwn(values, key)) return false;
      if (key === 'year') {
        const range = String(value).trim().match(/^(\d{4})(?:\s*[-–]\s*(\d{4}))?$/);
        return Boolean(range && Number(figure.year) >= Number(range[1]) && Number(figure.year) <= Number(range[2] || range[1]));
      }
      if (key === 'figure') {
        const normalize = text => String(text || '').replace(/\bfig(?:ure)?\.?\s*/gi, 'figure ').replace(/(\d)\s+(?=[a-z](?:[\s,).+&–-]|$))/gi, '$1').replace(/[–—−]/g, '-');
        return contains(normalize(values[key]), normalize(value));
      }
      return contains(values[key], value);
    });
  }
  function recordedColors(figure) {
    const value = [figure.sections?.['Color & encoding'], figure.pdf_reference?.candidate?.['Color & encoding'], ...(figure.colors?.hex_values || [])].join(' ');
    const colors = value.match(/#(?:[a-f0-9]{6}|[a-f0-9]{3})(?![a-z0-9_])/gi) || [];
    return [...new Set(colors.map(hex => hex.length === 4 ? '#'+[...hex.slice(1)].map(c => c+c).join('').toUpperCase() : hex.toUpperCase()))].slice(0, 8);
  }
  function sampleColors(pixels, limit = 6) {
    const colorful = new Map(), neutral = new Map();
    for (let i = 0; i + 3 < pixels.length; i += 4) {
      const [r, g, b, a] = pixels.slice(i, i + 4);
      if (a < 220 || Math.min(r, g, b) > 240) continue;
      const table = Math.max(r, g, b) - Math.min(r, g, b) >= 24 ? colorful : neutral;
      const key = [r, g, b].map(v => Math.floor(v / 24)).join(',');
      const group = table.get(key) || {count: 0, sum: [0, 0, 0]};
      group.count++; [r, g, b].forEach((v, j) => { group.sum[j] += v; }); table.set(key, group);
    }
    const groups = [...(colorful.size ? colorful : neutral).values()].sort((a, b) => b.count - a.count);
    const selected = [];
    for (const group of groups) {
      const rgb = group.sum.map(v => Math.round(v / group.count));
      if (selected.every(other => Math.hypot(...rgb.map((v, i) => v - other[i])) >= 60)) selected.push(rgb);
      if (selected.length >= limit) break;
    }
    return selected.map(rgb => '#'+rgb.map(v => v.toString(16).padStart(2, '0')).join('').toUpperCase());
  }
  return {sections, browsingCategories, categoryGroup, formatFigureReference, fields, matches, recordedColors, sampleColors};
});
