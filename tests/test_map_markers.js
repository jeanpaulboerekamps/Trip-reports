// Run with: node tests/test_map_markers.js (after installing Python app requirements).
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const fixture = JSON.parse(execFileSync('python3', ['-c', `
import json
import folium
from trip_overview import ExpandOverlappingTrips
world = folium.Map()
markers = [folium.CircleMarker(point).add_to(world) for point in [[23.6,58.5],[23.6,58.5],[4.2,73.5]]]
macro = ExpandOverlappingTrips(markers)
world.add_child(macro)
print(json.dumps({'map_name':world.get_name(), 'marker_names':[m.get_name() for m in markers],
                 'points':[[23.6,58.5],[23.6,58.5],[4.2,73.5]],
                 'script':str(macro._template.module.script(macro, {}))}))
`], {cwd:path.resolve(__dirname,'..'), encoding:'utf8'}));
function point(x,y) {return {x,y,distanceTo(p){return Math.hypot(this.x-p.x,this.y-p.y);}};}
const removed=[];
const handlers={};
const map={
  latLngToLayerPoint(ll){return point(ll.lng*100,ll.lat*100);},
  layerPointToLatLng(p){return {lat:p.y/100,lng:p.x/100};},
  removeLayer(line){removed.push(line);},
  on(name,fn){handlers[name]=fn;}
};
const markers=fixture.points.map(([lat,lng])=>({
  position:{lat,lng}, handlers:{}, closed:false,
  getLatLng(){return {...this.position};},
  setLatLng(p){this.position={...p};},
  on(name,fn){this.handlers[name]=fn;},
  closePopup(){this.closed=true;},
  bringToFront(){}
}));
const lines=[];
const context={L:{
  point,
  polyline(points,opts){const line={points,opts,addTo(){lines.push(this);return this;}};return line;},
  DomEvent:{stopPropagation(event){event.stopped=true;}}
}};
context[fixture.map_name]=map;
fixture.marker_names.forEach((name,i)=>context[name]=markers[i]);
vm.runInNewContext(fixture.script,context);
const original=markers.map(m=>({...m.position}));
markers[2].handlers.click({originalEvent:{}});
assert.deepEqual(markers.map(m=>m.position),original); // Oman and Maldives are never combined.
const click={originalEvent:{}};
markers[0].handlers.click(click);
assert.notDeepEqual(markers[0].position,original[0]);
assert.notDeepEqual(markers[1].position,original[1]);
assert.deepEqual(markers[2].position,original[2]);
assert.equal(lines.length,2);
assert.equal(click.originalEvent.stopped,true);
handlers.zoomstart();
assert.deepEqual(markers.map(m=>m.position),original);
assert.equal(removed.length,2);
markers[1].handlers.click({originalEvent:{}});
handlers.dragstart();
assert.deepEqual(markers.map(m=>m.position),original);
console.log('Map interaction: distant trips stay separate, coincident trips expand and reset on zoom/drag.');
