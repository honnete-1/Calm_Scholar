/* DOM workflow smoke test (not a browser layout/screenshot test).
   npm install, then npm test. */
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'..');
const htmlPath=process.argv[2]||path.join(root,'preview.html');
const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e));
const dom=new JSDOM(fs.readFileSync(htmlPath,'utf8'),{url:'https://example.test/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
const w=dom.window,d=w.document;
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.setInterval=()=>0;
w.eval(fs.readFileSync(path.join(root,'static/js/demo.js'),'utf8'));
w.eval(fs.readFileSync(path.join(root,'static/js/app.js'),'utf8'));
const tick=()=>new Promise(resolve=>setTimeout(resolve,15));
const click=selector=>{const el=d.querySelector(selector);assert.ok(el,selector);el.click();};
const submit=id=>{const f=d.querySelector(id);assert.ok(f,id);f.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));};
const route=async tab=>{w.location.hash=tab;w.dispatchEvent(new w.HashChangeEvent('hashchange'));await tick();};
(async()=>{
 await tick();assert.match(d.querySelector('#content').textContent,/A little clarity/);
 assert.equal(d.querySelector('#demo-banner').hidden,false);
 for(const tab of ['assignments','planner','companion','focus','checkins','settings','today']){await route(tab);assert.ok(d.querySelector('#content h1'),tab);}
 await route('assignments');click('[data-action="add-assignment"]');
 const form=d.querySelector('#assignment-form');form.elements.title.value='DOM test assignment';form.elements.course.value='Testing';form.elements.due.value=w.CalmDemo.state().today;form.elements.minutes.value='90';submit('#assignment-form');await tick();
 assert.ok(w.CalmDemo.state().assignments.some(a=>a.title==='DOM test assignment'));
 const a=w.CalmDemo.state().assignments.find(a=>a.title==='DOM test assignment');
 click(`[data-action="breakdown"][data-id="${a.id}"]`);await tick();assert.equal(w.CalmDemo.state().assignments.find(x=>x.id===a.id).steps.length,4);
 await route('planner');submit('#planner-form');await tick();assert.match(d.querySelector('#content').textContent,/This is a proposal/);
 click('[data-action="confirm-plan"]');await tick();assert.doesNotMatch(d.querySelector('#content').textContent,/This is a proposal/);
 await route('checkins');click('[data-mood="low"]');assert.equal(w.CalmDemo.state().checkins.length,0,'Mood selection must not submit the form');
 d.querySelector('#checkin-form textarea').value='A fictional reflection';submit('#checkin-form');await tick();assert.equal(w.CalmDemo.state().checkins[0].mood,'low');
 await route('companion');d.querySelector('#chat-input').value='I worked hard but my grade disappointed me';submit('#chat-form');await tick();assert.equal(d.querySelectorAll('.message').length,2);assert.equal(w.CalmDemo.state().messages.length,0,'History off by default');
 click('[data-action="clear-chat"]');await tick();assert.equal(d.querySelectorAll('.message').length,0);
 await route('settings');d.querySelector('[name="remember_chat"]').checked=true;submit('#settings-form');await tick();assert.equal(w.CalmDemo.state().profile.remember_chat,true);
 await route('companion');d.querySelector('#chat-input').value='Help me begin';submit('#chat-form');await tick();assert.equal(w.CalmDemo.state().messages.length,2);
 await route('focus');click('[data-action="timer-duration"][data-minutes="10"]');assert.equal(d.querySelector('#timer').textContent,'10:00');click('[data-action="timer-toggle"]');assert.match(d.querySelector('#timer-label').textContent,/One thing/);click('[data-action="timer-toggle"]');click('[data-action="timer-reset"]');assert.equal(d.querySelector('#timer').textContent,'10:00');
 click('[data-action="search"]');d.querySelector('#search-input').value='DOM test';d.querySelector('#search-input').dispatchEvent(new w.Event('input',{bubbles:true}));assert.equal(d.querySelectorAll('.search-result').length,1);
 assert.equal(errors.length,0,errors.map(e=>e.message).join('\n'));
 console.log('Frontend DOM workflows passed: navigation, CRUD, breakdown, planning, mood selection, chat privacy, timer controls, search.');
 dom.window.close();
})().catch(e=>{console.error(e);dom.window.close();process.exitCode=1;});
