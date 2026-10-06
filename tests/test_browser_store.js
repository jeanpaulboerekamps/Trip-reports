// Run with: node tests/test_browser_store.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const markup = fs.readFileSync(path.join(__dirname, '../local_store_component/index.html'), 'utf8');
const script = markup.match(/<script>([\s\S]*?)<\/script>/)[1];
const storage = new Map();
const messages = [];
let handler;
vm.runInNewContext(script, {
  localStorage: {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v)},
  window: {parent: {postMessage: data => messages.push(data)}, addEventListener: (_, fn) => handler = fn}
});
let counter = 0;
function render(args) {
  handler({data: {type: 'streamlit:render', args: {nonce: String(++counter), ...args}}});
  return messages[messages.length - 1].value;
}
const legacy = {id: 'trip-1', name: 'Reis', username: 'jeanpaulboerekamps',
  search: {username: 'jeanpaulboerekamps'}, summary: {species: 4}};
render({op: 'save', record: legacy});
const stamp = '2026-10-02T10:00:00+00:00';
const latest = {...legacy, search: {...legacy.search, calculated_at: stamp}, summary: {species: 6},
  versions: [{id: stamp, calculated_at: stamp,
    search: {...legacy.search, calculated_at: stamp}, summary: {species: 6}}]};
let result = render({op: 'save', record: latest});
assert.equal(result.records[0].versions.length, 2);
assert.equal(result.records[0].summary.species, 6);
result = render({op: 'save', record: latest});
assert.equal(result.records[0].versions.length, 2);
result = render({op: 'import', imported: [legacy]});
assert.equal(result.records[0].versions.length, 2);
assert.equal(result.records[0].summary.species, 6);
const token = 'a'.repeat(32);
result = render({op: 'list', active_report: token});
assert.equal(result.last_report, token);
// Reloading the component reads the actual persisted data and report reference.
let handler2;
vm.runInNewContext(script, {
  localStorage: {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v)},
  window: {parent: {postMessage: data => messages.push(data)}, addEventListener: (_, fn) => handler2 = fn}
});
handler2({data: {type: 'streamlit:render', args: {op: 'list', nonce: 'initial'}}});
result = messages[messages.length - 1].value;
assert.equal(result.records[0].summary.species, 6);
assert.equal(result.records[0].versions.length, 2);
assert.equal(result.last_report, token);
console.log('Browser storage: migration, save, import, repeat-save and reload passed.');
result = render({op: 'locations', locations: [{id: 'trip-1', map_location: [-1.4, 120.3]}]});
assert.equal(JSON.stringify(result.records[0].map_location), '[-1.4,120.3]');
assert.equal(result.records[0].summary.species, 6);
assert.equal(result.records[0].versions.length, 2);
render({op: 'save', record: {...legacy, id: 'trip-2', name: 'Andere trip'}});
result = render({op: 'delete', trip_id: 'trip-1'});
assert.equal(result.records.length, 1);
assert.equal(result.records[0].id, 'trip-2');
result = render({op: 'list'});
assert.equal(result.records.length, 1);
assert.equal(result.records[0].id, 'trip-2');
console.log('Map metadata updates and deletion of a selected trip with all versions passed.');
