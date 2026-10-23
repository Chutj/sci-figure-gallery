/* Synthetic fixtures only; no real rights decisions or original FIG writes. */
const test = require('node:test');
const assert = require('node:assert/strict');
const {matches, recordedColors, sampleColors} = require('../assets/js/gallery-tools.js');
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
