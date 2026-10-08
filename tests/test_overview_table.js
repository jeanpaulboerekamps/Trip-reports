// Test the embedded component protocol without requiring a browser or network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../app.py'), 'utf8');
// Python's repr escapes match JSON for this HTML, except single quotes.
const literal = source.match(/^_TRIP_TABLE_HTML = (.+)$/m)[1];
const html = JSON.parse(literal.startsWith('"') ? literal : '"'+literal.slice(1,-1).replace(/\\'/g,"'").replace(/"/g,'\\"')+'"');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.attrs={};this.events={};this.style={setProperty(){}};this.classList={toggle:(key,value)=>this.attrs[key]=value};}
 append(child){this.children.push(child);}replaceChildren(){this.children=[];}
 setAttribute(key,value){this.attrs[key]=value;}addEventListener(key,fn){this.events[key]=fn;}
 querySelector(){return this.children.flatMap(x=>x.children).find(x=>x.tag==='button');}
 getBoundingClientRect(){return {height:200};}
}
const nodes=Object.fromEntries(['colgroup','thead','tbody','.wrap','table'].map(key=>[key,new Element(key)]));
const messages=[];const handlers={};
const document={body:new Element('body'),createElement:tag=>new Element(tag),querySelector:key=>nodes[key],querySelectorAll:()=>nodes.tbody.children};
const window={parent:{postMessage:msg=>messages.push(msg)},addEventListener:(name,fn)=>handlers[name]=fn};
vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],{document,window,ResizeObserver:class{observe(){}},requestAnimationFrame:fn=>fn()});
const rows=[{id:'a',values:['<script>unsafe</script>','01-01-2026','02-01-2026','500','206','0','1','2','3','Onbekend','1']}];
const columns=['Trip','Van','Tot','Waarnemingen','Soorten','Niet op soort','Nieuw voor mij','Nieuw in gebied','Nieuw op iNat','Berekend op','Versies'];
const render=rows=>handlers.message({data:{type:'streamlit:render',args:{rows,columns}}});
render(rows);
assert.equal(nodes.tbody.children[0].querySelector().textContent,rows[0].values[0]);
assert.equal(nodes.thead.children[0].children[3].textContent,'Waar\u00adnemingen');
assert.equal(nodes.colgroup.children.reduce((sum,col)=>sum+parseFloat(col.style.width),0),100);
nodes.tbody.children[0].events.click();
assert.equal(messages.at(-1).value,'a');
render(rows);assert.equal(nodes.tbody.children[0].attrs.selected,true);
nodes.tbody.children[0].events.click();assert.equal(messages.at(-1).value,null);
render(rows);nodes.tbody.children[0].querySelector().events.click({stopPropagation(){}});assert.equal(messages.at(-1).value,'a');
render([{id:'b',values:rows[0].values}]);assert.equal(nodes.tbody.children[0].attrs.selected,false);
assert(html.includes('table-layout:fixed'));assert(html.includes('white-space:normal'));assert(html.includes('overflow-wrap:anywhere'));
console.log('Overview component: selection, deselection, escaping, headers and column proportions passed.');
