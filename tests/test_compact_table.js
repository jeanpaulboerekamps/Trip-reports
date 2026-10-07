// Optional DOM tests: npm install jsdom; node tests/test_compact_table.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {JSDOM} = require('jsdom');
const root = path.resolve(__dirname, '..');
const fixture = JSON.parse(execFileSync('python3', ['-c', `
import json
from trip_table_ui import COLUMNS, table_payload
from trip_store import make_record
from trip_overview import overview_map, ExpandOverlappingTrips
import folium
settings = {'username':'test', 'start':'2025-01-01', 'end':'2025-01-10', 'places':[], 'geometry':'', 'calculated_at':'2026-03-01T10:00:00+00:00'}
counts = {'observations':10, 'species':2, 'unidentified':1, 'own':1, 'area':None, 'global':0}
first = make_record('Z-trip', settings, counts, trip_id='low')
second = make_record('<img src=x onerror=alert(1)>', {**settings,'calculated_at':'2026-02-28T10:00:00+00:00'}, {**counts,'species':7, 'area':5}, trip_id='high')
third = make_record('A-trip', settings, {**counts,'species':4,'area':2}, trip_id='middle')
print(json.dumps({'rows':table_payload([first, second, third]), 'columns':COLUMNS}))
`], {cwd:root, encoding:'utf8'}));
const messages = [];
const dom = new JSDOM(fs.readFileSync(path.join(root, 'trip_table_component/index.html'), 'utf8'), {
  runScripts:'dangerously', pretendToBeVisual:true,
  beforeParse(window) { window.postMessage = data => messages.push(data); }
});
const window = dom.window;
const document = window.document;
const args = {...fixture, selected_id:null, context:'user-filter', sort_by:'Van', descending:true, order_signature:'order-a'};
function render(value=args) {window.dispatchEvent(new window.MessageEvent('message', {data:{type:'streamlit:render',args:value}}));}
function button(key) {return document.querySelector('button[aria-label="'+key+': sorteren"]');}
function rowOrder() {return [...document.querySelectorAll('tbody tr')].map(row=>row.dataset.tripId);}
render();
const headers = [...document.querySelectorAll('thead th')];
assert.equal(headers.length, 11);
assert.equal(headers[9].querySelector('button').getAttribute('aria-label'), 'Berekend op: sorteren');
assert.equal(headers[10].querySelector('button').getAttribute('aria-label'), 'Versies: sorteren');
assert.equal(button('Nieuw voor mij').querySelectorAll('.line').length, 2);
assert.equal(document.querySelectorAll('img').length, 0); // Names render as text, never HTML.
button('Soorten').click();
assert.deepEqual(rowOrder(), ['low','middle','high']);
button('Soorten').click();
assert.deepEqual(rowOrder(), ['high','middle','low']);
document.querySelector('tbody tr').click();
const selection = messages.filter(m=>m.type==='streamlit:setComponentValue').at(-1).value;
assert.equal(selection.selected_id, 'high');
assert.equal(selection.context, 'user-filter');
assert.equal(document.querySelector('tr[aria-selected="true"]').dataset.tripId, 'high');
render({...args, selected_id:'high'});
assert.deepEqual(rowOrder(), ['high','middle','low']); // Server rerender keeps local header sort.
button('Berekend op').click();
assert.equal(rowOrder()[0], 'high'); // February 28 sorts before March 1, regardless of display format.
button('Berekend op').click();
assert.equal(rowOrder().at(-1), 'high');
button('Nieuw in gebied').click();
assert.deepEqual(rowOrder(), ['middle','high','low']);
button('Nieuw in gebied').click();
assert.deepEqual(rowOrder(), ['high','middle','low']); // Unknown is last in both directions.
const selected = document.querySelector('tr[data-trip-id="high"]');
selected.dispatchEvent(new window.KeyboardEvent('keydown', {key:'Enter',bubbles:true}));
assert.equal(messages.filter(m=>m.type==='streamlit:setComponentValue').at(-1).value.selected_id, null);
render({...args, sort_by:'Soorten', descending:false, selected_id:null});
assert.deepEqual(rowOrder(), ['low','high','middle']); // External sort control resets local sort.
assert.equal(document.querySelector('th[aria-sort="ascending"] button').getAttribute('aria-label'), 'Soorten: sorteren');
window.close();
console.log('Compact table DOM: wrapped headers, column order, typed sorting, stable ID selection, keyboard and escaping passed.');
