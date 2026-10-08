const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname,'../ebird_ui.py'),'utf8').match(/_STORE_HTML = '''([\s\S]*?)'''/)[1];
const messages=[];
const handlers={};
const saved=new Map();
let fail=false;
let opened=0;
const indexedDB={open(){
 const request={};opened++;
 queueMicrotask(()=>{
  if(fail){request.error=new Error('Access denied');request.onerror();return;}
  request.result={createObjectStore(){},close(){},transaction(){
   const tx={objectStore(){return {put(data,key){const req={};queueMicrotask(()=>{saved.set(key,data);req.onsuccess();tx.oncomplete();});return req;},get(key){const req={};queueMicrotask(()=>{req.result=saved.get(key);req.onsuccess();tx.oncomplete();});return req;}};}};
   return tx;
  }};
  request.onupgradeneeded();request.onsuccess();
 });
 return request;
}};
const window={parent:{postMessage:msg=>messages.push(msg)},addEventListener:(name,fn)=>handlers[name]=fn};
vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],{window,indexedDB,Promise,Error});
const render=args=>handlers.message({data:{type:'streamlit:render',args}});
(async()=>{
 await render({op:'load',nonce:'initial'});
 assert.equal(messages.at(-1).value.data,null);
 const data={format:1,observations:[['2026-10-01',0,0,1]]};
 await render({op:'save',nonce:'save1',data});
 assert.equal(saved.get('personal'),data);
 assert.equal(messages.at(-1).value.data,data);
 const count=opened;
 await render({op:'save',nonce:'save1',data});assert.equal(opened,count);
 await render({op:'load',nonce:'reload'});assert.equal(messages.at(-1).value.data,data);
 fail=true;
 await render({op:'load',nonce:'failed'});assert.equal(messages.at(-1).value.error,'Access denied');
 assert.equal(saved.get('personal'),data);
 console.log('eBird persistence: empty load, save, reload, repeated nonce and storage failure passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
