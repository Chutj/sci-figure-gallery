/* Synthetic fixtures only; no real rights decisions or original FIG writes. */
const test = require('node:test');
const assert = require('node:assert/strict');
const {browsingCategories, categoryGroup, formatFigureReference, fields, matches, creditSegments, figureURL, resolveFigureLink, batch, createDetailLoader, recordedColors, sampleColors} = require('../assets/js/gallery-tools.js');
const figure = {
  title:'Drought response', paper:'A synthetic research paper', author:'Jane Example',
  doi:'10.1234/test', journal:'Example Journal', year:2026, figure:'Fig. 2 a–b',
  categories:['Maps', 'Regression'], sections:{
    'What the figure shows':'Regional drought patterns.', 'Statistics & symbols':'Linear regression.',
    'Color & encoding':'Blue and orange, #abcdef.', 'Design lessons':'Aligned panels.',
    'Verification & limitations':'Hidden-evidence-token',
  },
};
test('universal browsing tags are hidden without deleting source metadata or colors', () => {
  const record={...figure,categories:['Maps','Color references','Legends, color scales & symbols','Multi-panel layouts']};
  const before=JSON.stringify(record);
  assert.deepEqual(browsingCategories(record),['Maps','Multi-panel layouts']);
  assert.equal(matches(record,'','',{method:'color references'}),false);
  assert.equal(matches(record,'','',{color:'#abcdef'}),true);
  assert.deepEqual(recordedColors(record),['#ABCDEF']);
  assert.equal(JSON.stringify(record),before);
  assert.deepEqual(browsingCategories({}),[]);
});
test('remaining focus filters still narrow real records after universal tags are removed', () => {
  const fs=require('node:fs'),path=require('node:path');
  const records=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/gallery/public.json'),'utf8')).records;
  const labels=[...new Set(records.flatMap(browsingCategories))];
  assert.ok(!labels.includes('Color references'));
  assert.ok(!labels.includes('Legends, color scales & symbols'));
  for (const name of labels.filter(name=>categoryGroup(name)==='focus')) {
    const count=records.filter(r=>matches(r,'','',{},name)).length;
    assert.ok(count>0 && count<records.length,name);
  }
});
test('figure types and learning focuses are separated without changing records', () => {
  for (const label of ['Maps', 'Bar charts', 'Box, violin & raincloud plots', 'Sankey & chord diagrams'])
    assert.equal(categoryGroup(label), 'type');
  for (const label of ['Model evaluation', 'Paths & networks', 'Physical interpretation', 'SHAP plots', 'Schematics', 'Color references', 'Multi-panel layouts'])
    assert.equal(categoryGroup(label), 'focus');
  // Future source labels remain browsable instead of silently disappearing.
  assert.equal(categoryGroup('New source learning category'), 'focus');
});
test('figure type and focus intersect with keywords and advanced queries', () => {
  const record = {...figure, categories:['Maps','Model evaluation']};
  const before = JSON.stringify(record);
  assert.equal(matches(record,'drought','Maps',{journal:'Example'},'Model evaluation'),true);
  assert.equal(matches(record,'drought','Bar charts',{},'Model evaluation'),false);
  assert.equal(matches(record,'drought','Maps',{},'SHAP plots'),false);
  assert.equal(matches(record,'','',{},'Model evaluation'),true);
  assert.equal(matches(record,'','',{},''),true);
  assert.equal(matches({},'','',{},'Model evaluation'),false);
  assert.equal(JSON.stringify(record),before);
});
test('clearing both facets restores the full library, including focus-only figures', () => {
  const rows = [{...figure,categories:['Maps','Model evaluation']},
    {...figure,categories:['Bar charts','Color references']},
    {...figure,categories:['SHAP plots']}];
  const filter = (type,focus) => rows.filter(row => matches(row,'',type,{},focus));
  assert.equal(filter('Maps','Model evaluation').length,1);
  assert.equal(filter('Maps','Color references').length,0);
  assert.equal(filter('','SHAP plots').length,1);
  assert.equal(filter('','').length,3);
});
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
    ['Fig.3 left_density', 'Fig. 3'], ['Fig.5 right_bars', 'Fig. 5'],
    ['Fig.2 (panel label pending translation)', 'Fig. 2'],
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
  for (const handle of ['aims','stats','maps','photo','leftmaps','distributions','regional'])
    assert.equal(formatFigureReference('Fig.1 · '+handle),'Fig. 1');
});


test('compact index searches the same fields without loading full notes', () => {
  const compact = {id:'figure-synthetic', title:figure.title, year:figure.year, figure:figure.figure,
    categories:figure.categories, search_fields:fields(figure)};
  for (const [query, advanced] of [['regional drought',{}],['',{color:'#abcdef'}],
    ['',{method:'linear regression'}],['',{author:'jane',year:'2020–2026'}],
    ['2a–b',{}],['',{figure:'Figure 2 a-b'}],['hidden-evidence-token',{}]]) {
    assert.equal(matches(compact,query,'Maps',advanced),matches(figure,query,'Maps',advanced));
  }
  assert.equal(compact.sections,undefined);
});

test('batches preserve sorted order and global search reaches beyond first batch', () => {
  const records=Array.from({length:121},(_,i)=>({...figure,id:`f${i}`,title:i===120?'Unique end-of-library method':`Figure ${i}`}));
  const first=batch(records,0), second=batch(records,first.length), last=batch(records,96);
  assert.equal(first.length,48); assert.equal(second.length,48);assert.equal(last.length,25);
  assert.deepEqual([...first,...second,...last].map(r=>r.id),records.map(r=>r.id));
  assert.equal(batch(records,records.length).length,0);
  const found=records.filter(r=>matches(r,'end-of-library','',{}));
  assert.equal(batch(found,0)[0].id,'f120');
});

test('details load only on request, cache validated records and reject foreign paths', async () => {
  let calls=0;
  const full={...figure,id:'f1'};
  const load=createDetailLoader(async (url,options)=>{calls++;assert.equal(options.credentials,'omit');return {ok:true,json:async()=>full};},'https://example.test/gallery/');
  const card={id:'f1',details_url:'/gallery/records/f1/hash.json'};
  assert.equal(calls,0);
  assert.equal(await load(card),full);assert.equal(await load(card),full);assert.equal(calls,1);
  for (const details_url of ['https://elsewhere.test/f.json','//elsewhere.test/f.json','/file.html','/f.json?secret=x'])
    await assert.rejects(load({...card,details_url}));
  assert.equal(calls,1);
  assert.equal(await load(full),full);
  await assert.rejects(load({...card,id:'different-id'}));
});

test('failed or mismatched details are never cached and retry can succeed', async () => {
  const card={id:'f1',details_url:'/records/f1.json'};
  let attempt=0;
  const load=createDetailLoader(async ()=>{
    attempt++;
    return {ok:attempt!==1,json:async()=>({id:attempt===2?'wrong':'f1',sections:{}})};
  },'https://example.test/gallery/');
  await assert.rejects(load(card));
  await assert.rejects(load(card));
  assert.equal((await load(card)).id,'f1');
  assert.equal(attempt,3);
});

test('a cancelled in-flight detail cannot populate the cache after closing', async () => {
  let complete, calls=0;
  const card={id:'f1',details_url:'/records/f1.json'};
  const load=createDetailLoader(async ()=>{
    calls++;
    return {ok:true,json:()=>new Promise(resolve=>{complete=resolve;})};
  },'https://example.test/gallery/');
  const controller=new AbortController();
  const pending=load(card,controller.signal);
  await Promise.resolve();
  controller.abort();complete({id:'f1'});
  await assert.rejects(pending);
  const retry=load(card);await Promise.resolve();complete({id:'f1'});await retry;
  assert.equal(calls,2);
});


test('figure links use stable IDs while retaining unrelated query values and hash', () => {
  const initial='https://example.test/gallery/?campaign=group+meeting&lang=en#notes';
  const linked=new URL(figureURL(initial,'fig-stable id/β'));
  assert.equal(linked.pathname,'/gallery/');
  assert.equal(linked.searchParams.get('figure'),'fig-stable id/β');
  assert.equal(linked.searchParams.get('campaign'),'group meeting');
  assert.equal(linked.searchParams.get('lang'),'en');
  assert.equal(linked.hash,'#notes');
  assert.equal(figureURL(linked.href,'fig-stable id/β'),linked.href);
  const cleared=new URL(figureURL(linked.href,null));
  assert.equal(cleared.searchParams.has('figure'),false);
  assert.equal(cleared.searchParams.get('campaign'),'group meeting');
  assert.equal(cleared.hash,'#notes');
  assert.equal(new URL(figureURL(linked.href,'fig-next')).searchParams.getAll('figure').length,1);
});

test('direct figure links resolve against the entire catalog, never arbitrary assets', () => {
  const rows=Array.from({length:121},(_,i)=>({id:`fig-${i}`}));
  assert.equal(resolveFigureLink('https://example.test/gallery/?figure=fig-120',rows).figure,rows[120]);
  assert.equal(resolveFigureLink('https://example.test/gallery/',rows).status,'none');
  for (const suffix of ['?figure=missing','?figure=','?figure=fig-1&figure=fig-2',
    '?figure=https%3A%2F%2Fprivate.test%2Ffile.json','?figure=..%2Fprivate%2Ffile.pdf']) {
    const result=resolveFigureLink('https://example.test/gallery/'+suffix,rows);
    assert.equal(result.status,'unknown');assert.equal(result.figure,null);
  }
});


test('credit linkification keeps all prose and makes HTTPS attribution URLs actionable', () => {
  const credit='© OpenStreetMap contributors (https://www.openstreetmap.org/copyright). ODbL: https://opendatacommons.org/licenses/odbl/1.0/; no new license granted.';
  const segments=creditSegments(credit);
  assert.equal(segments.map(s=>s.text).join(''),credit);
  assert.deepEqual(segments.filter(s=>s.href).map(s=>s.href),[
    'https://www.openstreetmap.org/copyright','https://opendatacommons.org/licenses/odbl/1.0/']);
  assert.equal(creditSegments('Only original prose.')[0].text,'Only original prose.');
  assert.deepEqual(creditSegments(''),[]);
});

test('credit URLs cannot make script, credential, localhost or literal IP links', () => {
  for (const credit of ['javascript:alert(1)','http://example.org/copyright',
    'https://localhost/','https://host.local/','https://internal.test/','https://127.0.0.1/',
    'https://2130706433/','https://0x7f000001/','https://[::1]/','https://192.168.1.2/',
    'https://user:password@example.org/','https://example.org:8443/']) {
    const segments=creditSegments(credit);
    assert.equal(segments.map(s=>s.text).join(''),credit);
    assert.equal(segments.some(s=>s.href),false,credit);
  }
  const html='<img src=x onerror=alert(1)> https://www.openstreetmap.org/copyright';
  const segments=creditSegments(html);
  assert.equal(segments.map(s=>s.text).join(''),html);
  assert.ok(segments[0].text.includes('<img'));
});

test('linkifying all existing approved credits preserves their text byte for byte', () => {
  const fs=require('node:fs'),path=require('node:path');
  const records=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/gallery/public.json'),'utf8')).records;
  for (const record of records) for (const key of ['attribution','additional_credit']) {
    const credit=record.rights?.[key] || '';
    assert.equal(creditSegments(credit).map(s=>s.text).join(''),credit,record.id+' '+key);
  }
});
