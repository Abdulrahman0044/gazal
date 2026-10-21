import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act} from 'react';
import {createRoot} from 'react-dom/client';
import AuthForm from '../components/AuthForm';
import WorkspaceShell from '../components/WorkspaceShell';
const dom=new JSDOM('<!doctype html><div id="root"></div>',{url:'http://localhost:3000/signup'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,location:dom.window.location,history:dom.window.history,sessionStorage:dom.window.sessionStorage,FormData:dom.window.FormData,AbortController:dom.window.AbortController,IS_REACT_ACT_ENVIRONMENT:true});
const host=document.getElementById('root')!;
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
function fill(id:string,value:string){(document.getElementById(id) as HTMLInputElement).value=value;}
async function submit(form:HTMLFormElement){await act(async()=>{form.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));await tick()});}
let calls:{path:string;body:any}[]=[];
function mock(responder:(path:string,body:any)=>any){calls=[];globalThis.fetch=async(input:any,options:any)=>{const path=String(input);const body=options?.body?JSON.parse(options.body):undefined;calls.push({path,body});const result=responder(path,body);return {ok:result.status===undefined||result.status<400,status:result.status||200,json:async()=>result.data??result} as Response};}
test('React signup submits once, rejects mismatches, and links to shared sign-in',async()=>{
 mock(()=>({id:'created'}));
 const root=createRoot(host);await act(async()=>root.render(<AuthForm mode="signup"/>));
 fill('signupName','Ada Gazal');fill('signupEmail','ada@example.test');fill('signupPassword','long-test-password');fill('signupConfirm','different-password');
 await submit(host.querySelector('form')!);assert.equal(calls.length,0);assert.match(host.textContent!,/passwords do not match/);
 fill('signupConfirm','long-test-password');await submit(host.querySelector('form')!);
 assert.deepEqual(calls[0],{path:'/api/signup',body:{name:'Ada Gazal',email:'ada@example.test',password:'long-test-password'}});
 assert.match(host.textContent!,/Your account is ready/);assert.equal(host.querySelector('a.primary')?.getAttribute('href'),'/signin');
 await act(async()=>root.unmount());
});
test('React sign-in displays backend errors and does not persist a failed session',async()=>{
 mock(()=>({status:401,data:{detail:'Invalid credentials'}}));sessionStorage.clear();
 const root=createRoot(host);await act(async()=>root.render(<AuthForm mode="signin"/>));
 // The controlled email state is set via the native input event.
 const input=host.querySelector('#signinEmail') as HTMLInputElement;
 Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(input,'ada@example.test');
 await act(async()=>input.dispatchEvent(new dom.window.Event('input',{bubbles:true})));
 fill('signinPassword','long-test-password');await submit(host.querySelector('form')!);
 assert.equal(calls[0].path,'/api/login');assert.match(host.textContent!,/Invalid credentials/);assert.equal(sessionStorage.getItem('pt_token'),null);assert.equal(host.querySelector('a[href="/signup"]')?.textContent,'Create an account ↗');
 await act(async()=>root.unmount());
});
test('invitation signup freezes invited identity and accepts the token',async()=>{
 history.replaceState(null,'','/join#token=abcdefghijklmnopqrstuvwx');
 mock(path=>path.endsWith('/inspect')?{name:'Invited Ada',email:'ada@example.test',account:'GAZAL team',role:'employee',existing_user:false}:{id:'joined'});
 const root=createRoot(host);await act(async()=>{root.render(<AuthForm mode="signup"/>);await tick()});
 assert.equal((document.getElementById('signupEmail') as HTMLInputElement).readOnly,true);assert.equal(location.hash,'');
 fill('signupPassword','long-test-password');fill('signupConfirm','long-test-password');await submit(host.querySelector('form')!);
 assert.equal(calls.at(-1)?.path,'/api/invitations/accept');assert.equal(calls.at(-1)?.body.token,'abcdefghijklmnopqrstuvwx');
 await act(async()=>root.unmount());history.replaceState(null,'','/app');
});
test('workspace preserves employee restrictions and removes polling on unmount',async()=>{
 sessionStorage.setItem('pt_token','test-token');
 mock(path=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/accounts')return [{id:'team',name:'Team',role:'employee'}];
  if(path.endsWith('/dashboard'))return {total:0,approved:0,overdue:0,active_projects:0,status_counts:{},recent_tasks:[]};
  return [];
 });
 const timers=new Set<any>();const original=window.setInterval.bind(window);const clear=window.clearInterval.bind(window);
 window.setInterval=((...args:any[])=>{const id=original(args[0],args[1]);timers.add(id);return id}) as any;
 window.clearInterval=((id:any)=>{timers.delete(id);clear(id)}) as any;
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 assert.equal((host.querySelector('[data-view="performance"]') as HTMLElement).hidden,true);
 assert.equal((host.querySelector('[data-view="remote"]') as HTMLElement).hidden,true);
 assert.equal((host.querySelector('#app') as HTMLElement).hidden,false);assert.equal(timers.size,3);
 assert.equal(typeof (window as any).go,'function');assert.equal(sessionStorage.getItem('pt_token'),'test-token');assert.match(host.textContent!,/Completion progress/);
 await act(async()=>root.unmount());assert.equal(timers.size,0);assert.equal((window as any).go,undefined);
 window.setInterval=original;window.clearInterval=clear;
});
test('workspace keeps a valid session and shows startup API errors instead of sign-in',async()=>{
 sessionStorage.setItem('pt_token','test-token');
 mock(path=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/accounts')return [{id:'team',name:'Team',role:'employee'}];
  if(path.endsWith('/dashboard'))return {status:503,data:{detail:'Database temporarily unavailable'}};
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 assert.equal(sessionStorage.getItem('pt_token'),'test-token');
 assert.equal((host.querySelector('#login') as HTMLElement).hidden,true);
 assert.equal((host.querySelector('#app') as HTMLElement).hidden,false);
 assert.equal((host.querySelector('#workspaceLoading') as HTMLElement).hidden,true);
 assert.match(host.textContent!,/Could not load business overview/);
 assert.match(host.textContent!,/Database temporarily unavailable/);
 await act(async()=>root.unmount());
});
test('workspace accepts a pending invitation before loading the account view',async()=>{
 sessionStorage.setItem('pt_token','test-token');
 sessionStorage.setItem('gazal_pending_invite','pending-invite-token');
 mock(path=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/invitations/accept')return {ok:true};
  if(path==='/api/accounts')return [{id:'team',name:'Team',role:'employee'}];
  if(path.endsWith('/dashboard'))return {total:0,approved:0,overdue:0,active_projects:0,status_counts:{}};
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 const acceptIndex=calls.findIndex(call=>call.path==='/api/invitations/accept');
 const accountsIndex=calls.findIndex(call=>call.path==='/api/accounts');
 assert.ok(acceptIndex>=0&&acceptIndex<accountsIndex);
 assert.equal(sessionStorage.getItem('gazal_pending_invite'),null);
 assert.equal((host.querySelector('#workspaceLoading') as HTMLElement).hidden,true);
 assert.equal((host.querySelector('#app') as HTMLElement).hidden,false);
 assert.doesNotMatch(host.textContent!,/paste your invitation link below/i);
 await act(async()=>root.unmount());
});
test('workspace shows the branded loader while the session is being checked',async()=>{
 sessionStorage.setItem('pt_token','slow-token');
 let resolveMe!:()=>void;
 const waitingForMe=new Promise<void>(resolve=>{resolveMe=resolve});
 globalThis.fetch=async(input:any,options:any)=>{
  const path=String(input);calls.push({path,body:options?.body?JSON.parse(options.body):undefined});
  if(path==='/api/me'){await waitingForMe;return {ok:true,status:200,json:async()=>({id:'ada',name:'Ada',is_super:false})} as Response}
  return {ok:true,status:200,json:async()=>[]} as Response;
 };
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 assert.equal((host.querySelector('#workspaceLoading') as HTMLElement).hidden,false);
 assert.equal((host.querySelector('#login') as HTMLElement).hidden,true);
 assert.equal((host.querySelector('#app') as HTMLElement).hidden,true);
 resolveMe();
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,40))});
 assert.equal((host.querySelector('#workspaceLoading') as HTMLElement).hidden,true);
 await act(async()=>root.unmount());
});
test('workspace sidebar slides open and closed on narrow screens',async()=>{
 sessionStorage.setItem('pt_token','mobile-token');
 const originalMatchMedia=window.matchMedia;
 window.matchMedia=(()=>({matches:true,media:'(max-width: 760px)',onchange:null,addListener:()=>{},removeListener:()=>{},addEventListener:()=>{},removeEventListener:()=>{},dispatchEvent:()=>false})) as any;
 mock(path=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/accounts')return [];
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 const app=host.querySelector('#app') as HTMLElement;
 const toggle=host.querySelector('#sidebarToggle') as HTMLButtonElement;
 const backdrop=host.querySelector('#sidebarBackdrop') as HTMLElement;
 assert.ok(app.classList.contains('sidebar-closed'));
 assert.equal(toggle.getAttribute('aria-expanded'),'false');
 await act(async()=>toggle.click());
 assert.ok(app.classList.contains('sidebar-open'));
 assert.equal(toggle.getAttribute('aria-expanded'),'true');
 assert.equal(backdrop.hidden,false);
 await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true})));
 assert.ok(app.classList.contains('sidebar-closed'));
 assert.equal(backdrop.hidden,true);
 await act(async()=>toggle.click());
 await act(async()=>backdrop.click());
 assert.ok(app.classList.contains('sidebar-closed'));
 await act(async()=>root.unmount());
 window.matchMedia=originalMatchMedia;
});
test('workspace sidebar remains toggleable on wide screens without a mobile backdrop',async()=>{
 sessionStorage.setItem('pt_token','desktop-token');
 const originalMatchMedia=window.matchMedia;
 window.matchMedia=(()=>({matches:false,media:'(max-width: 760px)',onchange:null,addListener:()=>{},removeListener:()=>{},addEventListener:()=>{},removeEventListener:()=>{},dispatchEvent:()=>false})) as any;
 mock(path=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/accounts')return [];
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 const app=host.querySelector('#app') as HTMLElement;
 const toggle=host.querySelector('#sidebarToggle') as HTMLButtonElement;
 const backdrop=host.querySelector('#sidebarBackdrop') as HTMLElement;
 assert.ok(app.classList.contains('sidebar-open'));
 assert.equal(toggle.getAttribute('aria-expanded'),'true');
 assert.equal(backdrop.hidden,true);
 await act(async()=>toggle.click());
 assert.ok(app.classList.contains('sidebar-closed'));
 assert.equal(toggle.getAttribute('aria-expanded'),'false');
 assert.equal(backdrop.hidden,true);
 await act(async()=>toggle.click());
 assert.ok(app.classList.contains('sidebar-open'));
 await act(async()=>root.unmount());
 window.matchMedia=originalMatchMedia;
});
test('workspace navigation renders the selected page after loading its data',async()=>{
 sessionStorage.setItem('pt_token','navigation-token');
 mock(path=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/accounts')return [{id:'team',name:'Team',role:'account_admin'}];
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 await act(async()=>{(host.querySelector('[data-view="projects"]') as HTMLButtonElement).click();await tick()});
 assert.equal(host.querySelector('#pageTitle')?.textContent,'Projects');
 assert.match(host.querySelector('#content')?.textContent||'',/Account projects \(0\)/);
 assert.equal(host.querySelector('[data-view="projects"]')?.classList.contains('active'),true);
 await act(async()=>root.unmount());
});
test('traction report and data sources support dated manual counts',async()=>{
 sessionStorage.setItem('pt_token','traction-token');
 let activeUsers=21,manualSource=false;
 const metrics=[
  ['total_users','Registered users','count','snapshot'],['active_users','Daily active users','count','snapshot'],
  ['weekly_active_users','Weekly active users','count','snapshot'],['monthly_active_users','Monthly active users','count','snapshot'],
  ['new_signups','New sign-ups','count','flow'],['activated_users','Activated users','count','flow'],
  ['activation_rate','Activation rate','%','snapshot'],['posts_published','Posts published','count','flow'],
  ['paying_customers','Paying customers','count','snapshot'],['organic_social','Organic social sign-ups','count','flow'],
  ['organic_search','Organic search sign-ups','count','flow'],['paid_campaign','Paid campaign sign-ups','count','flow'],
  ['referrals','Referral / community sign-ups','count','flow'],['direct_signups','Direct / unknown sign-ups','count','flow'],
  ['website_visitors','Website visitors','count','flow'],['registered_period','Registered in period','count','flow'],
  ['connected_accounts','Connected accounts','count','snapshot'],['first_posts','First posts','count','flow'],
  ['scheduling_users','Scheduling users','count','snapshot'],['ai_tool_users','AI tool users','count','snapshot'],
  ['analytics_users','Analytics users','count','snapshot'],['sentiment_users','Sentiment users','count','snapshot'],
  ['multi_member_workspaces','Multi-member workspaces','count','snapshot'],['returning_users','Returning users','count','snapshot'],
  ['dormant_users','Dormant users','count','snapshot'],['trials_started','Trials started','count','flow'],
  ['paid_conversions','Paid conversions','count','flow'],['mrr','Monthly recurring revenue','NGN','snapshot'],
  ['billed','Billed','NGN','flow'],['collected','Collected','NGN','flow'],['refunds','Refunds','NGN','flow'],
  ['starter_users','Starter users','count','snapshot'],['professional_users','Professional users','count','snapshot'],
  ['advanced_users','Advanced users','count','snapshot'],['individual_accounts','Individual accounts','count','snapshot'],
  ['creator_accounts','Creator accounts','count','snapshot'],['small_business_accounts','Small business accounts','count','snapshot'],
  ['brand_accounts','Brand accounts','count','snapshot'],['enterprise_accounts','Enterprise accounts','count','snapshot'],
  ['influencer_accounts','Influencer accounts','count','snapshot'],['marketing_team_accounts','Marketing team accounts','count','snapshot']
 ];
 mock((path,body)=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/accounts')return [{id:'team',name:'Team',role:'account_admin'}];
  if(path.endsWith('/projects'))return [{id:'project',name:'Growth'}];
  if(path.endsWith('/traction?')||path.includes('/traction?'))return {metrics:metrics.map(([key,label,unit,aggregation])=>({key,label,unit,aggregation,value:key==='active_users'?activeUsers:null,as_of:key==='active_users'?'2026-10-20':null,source:key==='active_users'?'manual':null})),history:[]};
  if(path.endsWith('/sources')&&body?.mode==='manual'){manualSource=true;return {id:'source',metric:'active_users',mode:'manual'};}
  if(path.endsWith('/sources'))return manualSource?[{metric:'active_users',mode:'manual'}]:[];
  if(path.endsWith('/manual')){activeUsers=body.value;return {ok:true};}
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 await act(async()=>{(host.querySelector('[data-view="traction"]') as HTMLButtonElement).click();await tick()});
 assert.match(host.querySelector('#content')?.textContent||'',/Executive snapshot/);
 assert.match(host.querySelector('#content')?.textContent||'',/Acquisition & activation/);
 await act(async()=>{(host.querySelector('[data-view="sources"]') as HTMLButtonElement).click();await tick()});
 assert.match(host.querySelector('#content')?.textContent||'',/Enter a figure manually/);
 await act(async()=>{(host.querySelector('[data-source="active_users"][data-mode="manual"]') as HTMLButtonElement).click();await tick()});
 const metric=host.querySelector('#manualMetric') as HTMLSelectElement;metric.value='active_users';
 await act(async()=>metric.dispatchEvent(new dom.window.Event('change',{bubbles:true})));
 fill('manualValue','34');
 await act(async()=>{host.querySelector('#manualForm')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));await tick()});
 assert.deepEqual(calls.find(call=>call.path.endsWith('/manual'))?.body,{metric:'active_users',date:(host.querySelector('#manualDate') as HTMLInputElement).value,value:34});
 assert.match(host.querySelector('#content')?.textContent||'',/Manual source selected/);
 await act(async()=>root.unmount());
});
test('workspace navigation shows a retryable error if a required request fails',async()=>{
 sessionStorage.setItem('pt_token','navigation-error-token');
 mock(path=>{
  if(path==='/api/me')return {id:'ada',name:'Ada',is_super:false};
  if(path==='/api/accounts')return [{id:'team',name:'Team',role:'account_admin'}];
  if(path.endsWith('/projects'))return {status:503,data:{detail:'Project service unavailable'}};
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 await act(async()=>{(host.querySelector('[data-view="projects"]') as HTMLButtonElement).click();await tick()});
 assert.equal(host.querySelector('#pageTitle')?.textContent,'Projects');
 assert.match(host.querySelector('#content')?.textContent||'',/Could not load projects/);
 assert.match(host.querySelector('#content')?.textContent||'',/Project service unavailable/);
 assert.ok(host.querySelector('#retryView'));
 await act(async()=>root.unmount());
});
test('admin workspace opens performance policy and notification dropdown',async()=>{
 sessionStorage.setItem('pt_token','admin-token');
 mock(path=>{
  if(path==='/api/me')return {id:'admin',name:'Admin',is_super:false};
  if(path==='/api/accounts')return [{id:'team',name:'Team',role:'account_admin'}];
  if(path.endsWith('/dashboard'))return {total:0,approved:0,overdue:0,active_projects:0,status_counts:{}};
  if(path.endsWith('/policy-settings'))return {active:{name:'Delivery policy',version:1},versions:[]};
  return [];
 });
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 assert.equal((host.querySelector('[data-view="performance"]') as HTMLElement).hidden,false);
 await act(async()=>{await (window as any).go('performance')});assert.match(host.textContent!,/Employee performance/);
 await act(async()=>{(host.querySelector('#showPerformancePolicy') as HTMLButtonElement).click();await tick()});
 assert.match(host.textContent!,/Delivery policy/);assert.ok(calls.some(c=>c.path.endsWith('/policy-settings')));
 await act(async()=>{(host.querySelector('#notificationToggle') as HTMLButtonElement).click();await tick()});
 assert.equal((host.querySelector('#notificationDropdown') as HTMLElement).hidden,false);assert.equal(host.querySelector('#notificationToggle')?.getAttribute('aria-expanded'),'true');
 await act(async()=>{(host.querySelector('#notificationToggle') as HTMLButtonElement).click()});assert.equal((host.querySelector('#notificationDropdown') as HTMLElement).hidden,true);
 await act(async()=>root.unmount());
});
test('Strict Mode cancels initial workspace boot without logging out the next mount',async()=>{
 sessionStorage.setItem('pt_token','strict-token');
 const responder=(path:string)=>path==='/api/me'?{id:'ada',name:'Ada'}:[];
 globalThis.fetch=async(input:any,options:any)=>{await tick();if(options?.signal.aborted)throw new dom.window.DOMException('Aborted','AbortError');return {ok:true,status:200,json:async()=>responder(String(input))} as Response;};
 const root=createRoot(host);await act(async()=>{root.render(<React.StrictMode><WorkspaceShell/></React.StrictMode>);await new Promise(r=>setTimeout(r,50))});
 // Effects begin at the end of the render act; flush their asynchronous boot too.
 await act(async()=>{await new Promise(r=>setTimeout(r,50))});
 assert.equal(sessionStorage.getItem('pt_token'),'strict-token');assert.match(host.textContent!,/Your account is ready/);
 await act(async()=>root.unmount());
});
test('workspace renders the overview without waiting for optional startup requests',async()=>{
 sessionStorage.setItem('pt_token','fast-dashboard-token');
 let releaseOptional!:()=>void;
 const optionalRequests=new Promise<void>(resolve=>{releaseOptional=resolve});
 globalThis.fetch=async(input:any)=>{
  const path=String(input);calls.push({path,body:undefined});
  if(/\/(projects|employees|notifications|presence)$/.test(path))await optionalRequests;
  const data=path==='/api/me'?{id:'ada',name:'Ada',is_super:false}:
   path==='/api/accounts'?[{id:'team',name:'Team',role:'account_admin'}]:
   path.endsWith('/dashboard')?{total:0,approved:0,overdue:0,active_projects:0,status_counts:{}}:[];
  return {ok:true,status:200,json:async()=>data} as Response;
 };
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await new Promise(resolve=>setTimeout(resolve,40))});
 assert.match(host.querySelector('#content')?.textContent||'',/Completion progress/);
 assert.equal((host.querySelector('#workspaceLoading') as HTMLElement).hidden,true);
 assert.equal((host.querySelector('#app') as HTMLElement).hidden,false);
 assert.ok(calls.some(call=>call.path.endsWith('/dashboard')));
 releaseOptional();
 await act(async()=>{await tick()});
 await act(async()=>root.unmount());
});
test('workspace navigation keeps current content while page data loads and avoids unrelated requests',async()=>{
 sessionStorage.setItem('pt_token','navigation-cache-token');
 calls=[];
 let releaseProjects!:()=>void;
 const projectsPending=new Promise<void>(resolve=>{releaseProjects=resolve});
 globalThis.fetch=async(input:any,options:any)=>{
  const path=String(input);const body=options?.body?JSON.parse(options.body):undefined;calls.push({path,body});
  if(path.endsWith('/projects'))await projectsPending;
  const data=path==='/api/me'?{id:'ada',name:'Ada',is_super:false}:
   path==='/api/accounts'?[{id:'team',name:'Team',role:'account_admin'}]:
   path.endsWith('/dashboard')?{total:0,approved:0,overdue:0,active_projects:0,status_counts:{}}:
   path.endsWith('/projects')?[{id:'project',name:'Project'}]:[];
  return {ok:true,status:200,json:async()=>data} as Response;
 };
 const root=createRoot(host);await act(async()=>{root.render(<WorkspaceShell/>);await tick()});
 assert.match(host.querySelector('#content')?.textContent||'',/Completion progress/);
 await act(async()=>{(host.querySelector('[data-view="projects"]') as HTMLButtonElement).click();await tick()});
 assert.match(host.querySelector('#content')?.textContent||'',/Completion progress/);
 assert.doesNotMatch(host.querySelector('#content')?.textContent||'',/Loading projects/);
 assert.equal(host.querySelector('#content')?.getAttribute('aria-busy'),'true');
 releaseProjects();
 await act(async()=>{await tick()});
 assert.match(host.querySelector('#content')?.textContent||'',/Account projects \(1\)/);
 const projectCalls=calls.filter(call=>call.path.endsWith('/projects'));
 const employeeCalls=calls.filter(call=>call.path.endsWith('/employees'));
 await act(async()=>root.unmount());
 assert.equal(projectCalls.length,1);
 assert.equal(employeeCalls.length,0);
});
