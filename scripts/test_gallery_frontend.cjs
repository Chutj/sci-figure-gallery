/* Synthetic fixtures only; no real rights decisions or original FIG writes. */
const test = require('node:test');
const assert = require('node:assert/strict');
const {formatFigureReference, matches, recordedColors, sampleColors} = require('../assets/js/gallery-tools.js');
const figure = {
  title:'Drought response', paper:'A synthetic research paper', author:'Jane Example',
  doi:'10.1234/test', journal:'Example Journal', year:2026, figure:'Fig. 2 a–b',
  categories:['Maps', 'Regression'], sections:{
    'What the figure shows':'Regional drought patterns.', 'Statistics & symbols':'Linear regression.',
    'Color & encoding':'Blue and orange, #abcdef.', 'Design lessons':'Aligned panels.',
    'Verification & limitations':'Hidden-evidence-token',
  },
};
test('field queries use AND across fields and terms, ignoring case', () => {
  assert.equal(matches(figure,'drought','Maps',{author:'JANE example',journal:'example',doi:'10.1234'}),true);
  assert.equal(matches(figure,'drought','Maps',{author:'Other person'}),false);
  assert.equal(matches(figure,'drought','Other category',{}),false);
  assert.equal(matches(figure,'drought','',{journal:'Example missing'}),false);
});
test('year ranges are inclusive; invalid and reversed ranges do not match', () => {
  for (const year of ['2026','2020–2026','2026-2027']) assert.equal(matches(figure,'','',{year}),true);
  for (const year of ['2025','2027-2026','202','nonsense']) assert.equal(matches(figure,'','',{year}),false);
});
test('Figure search understands Fig. and Figure without widening other fields', () => {
  assert.equal(matches(figure,'','',{figure:'Figure 2'}),true);
  assert.equal(matches(figure,'','',{figure:'Fig. 2'}),true);
  assert.equal(matches(figure,'','',{figure:'Figure 3'}),false);
});
test('removed presentation section is not searchable; scientific methods remain searchable', () => {
  assert.equal(matches(figure,'hidden-evidence-token','',{}),false);
  assert.equal(matches(figure,'','',{method:'regression'}),true);
  assert.equal(matches(figure,'','',{color:'#abcdef'}),true);
});
test('missing fields do not crash; unknown filter fields fail closed', () => {
  assert.equal(matches({},'','',{}),true);
  assert.equal(matches({},'','',{author:'Someone'}),false);
  assert.equal(matches(figure,'','',{toString:'object'}),false);
});
test('local English candidates remain searchable without exposing hidden review prose', () => {
  const local = {pdf_reference:{candidate_title:'Draft diagram',candidate:{'Design lessons':'Sankey flows','Verification & limitations':'private-token'}}};
  assert.equal(matches(local,'sankey','',{}),true);
  assert.equal(matches(local,'private-token','',{}),false);
});
test('HEX values normalize shorthand and duplicates, rejecting malformed suffixes', () => {
  const source={sections:{'Color & encoding':'#abc #AABBCC #123456 #12345 #FFFFFFG #1234567'}};
  assert.deepEqual(recordedColors(source),['#AABBCC','#123456']);
});
test('palette ignores white, transparent pixels and neutral axes when accent colors exist', () => {
  const pixels=new Uint8ClampedArray([255,255,255,255,0,0,0,0,0,0,0,255,255,0,0,255,0,0,255,255]);
  assert.deepEqual(sampleColors(pixels),['#FF0000','#0000FF']);
});
test('grayscale figures retain useful neutral colors and obey sample limits', () => {
  assert.deepEqual(sampleColors(new Uint8ClampedArray([0,0,0,255,128,128,128,255])),['#000000','#808080']);
  assert.deepEqual(sampleColors(new Uint8ClampedArray([255,255,255,255])),[]);
  assert.equal(sampleColors(new Uint8ClampedArray([255,0,0,255,0,255,0,255]),1).length,1);
});


test('figure references share abbreviation, spacing, panel ranges and no redundant qualifiers', () => {
  const cases = [
    ['Fig.1 a-c', 'Fig. 1a–c'], ['Figure3 b', 'Fig. 3b'],
    ['Figure 5 (a)', 'Fig. 5a'], ['FIG. 2 (A-B)', 'Fig. 2A–B'],
    ['Figure 3 (complete)', 'Fig. 3'], ['Fig.5 Full figure', 'Fig. 5'],
    ['Fig.6 Full figure (user-provided)', 'Fig. 6'], ['Fig. 1 All', 'Fig. 1'],
    ['Fig.3 a maps', 'Fig. 3a'], ['Figure 2 (a_hist)', 'Fig. 2a'],
    ['Fig.3 a-c+e-g maps', 'Fig. 3a–c,e–g'], ['Fig.3 b+d+f bars', 'Fig. 3b,d,f'],
    ['Fig.3 central map', 'Fig. 3'], ['Figure 6 (right box-plot panels)', 'Fig. 6'],
  ];
  for (const [raw, expected] of cases) assert.equal(formatFigureReference(raw), expected, raw);
});

test('panel case and nonconsecutive selections survive; unfamiliar references are not guessed', () => {
  assert.equal(formatFigureReference('Fig.2 C-D'), 'Fig. 2C–D');
  assert.equal(formatFigureReference('Fig.2 a+c+e maps'), 'Fig. 2a,c,e');
  for (const raw of ['Extended Data Fig. 1a', 'Supplementary Fig. S1', 'Fig. 2 unlabelled inset'])
    assert.equal(formatFigureReference(raw), raw);
  assert.equal(formatFigureReference(null), '');
  const source = {figure:'Fig.2 C-D'};
  formatFigureReference(source.figure);
  assert.equal(source.figure, 'Fig.2 C-D');
});

test('compact displayed figure references remain searchable alongside source spellings', () => {
  for (const input of ['Fig. 2a', 'Figure 2 a', 'Fig. 2a–b', 'Figure 2 a-b'])
    assert.equal(matches(figure, '', '', {figure:input}), true, input);
  assert.equal(matches(figure, '2a–b', '', {}), true);
  assert.equal(matches(figure, '', '', {figure:'Fig. 3a'}), false);
});

test('every current public reference can be formatted without touching approved data', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const records = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/gallery/public.json'), 'utf8')).records;
  const before = JSON.stringify(records);
  for (const item of records) {
    const label = formatFigureReference(item.figure);
    assert.match(label, /^Fig\. \d+(?:[a-zA-Z]\d*(?:–[a-zA-Z]\d*)?(?:,[a-zA-Z]\d*(?:–[a-zA-Z]\d*)?)*)?$/, item.figure);
    assert.equal(formatFigureReference(label), label);
  }
  assert.equal(JSON.stringify(records), before);
});


test('new FIG batch separators and compact panel selections keep their exact membership', () => {
  const cases = [['Fig.2 · cd','Fig. 2c–d'],['Fig.1 · ABCEFG','Fig. 1A–C,E–G'],['Fig.3 · ch','Fig. 3c,h'],['Fig.2 · a1b1','Fig. 2a1,b1']];
  for (const [raw,expected] of cases) assert.equal(formatFigureReference(raw),expected);
  for (const handle of ['aims','stats','maps','photo','leftmaps','distributions'])
    assert.equal(formatFigureReference('Fig.1 · '+handle),'Fig. 1');
});
