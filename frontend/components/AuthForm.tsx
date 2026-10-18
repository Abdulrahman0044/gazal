'use client';
import {useEffect, useState, type FormEvent} from 'react';
import {ApiError, authRequest, parseInvitation} from '../lib/api';
type Invitation = {name:string; email:string; account:string; project?:string; role?:string; existing_user:boolean};
function Password({id,label,signup=false}:{id:string;label:string;signup?:boolean}) {
  const [visible,setVisible] = useState(false);
  return <><label htmlFor={id}>{label}</label><div className="password-field"><input id={id} name={id} type={visible?'text':'password'} required minLength={signup?14:undefined} maxLength={signup?200:undefined} autoComplete={signup?'new-password':'current-password'} placeholder={signup?'At least 14 characters':'Enter your password'}/><button type="button" aria-label={visible?'Hide password':'Show password'} onClick={()=>setVisible(!visible)}>{visible?'Hide':'Show'}</button></div></>;
}
export default function AuthForm({mode}:{mode:'signin'|'signup'}) {
  const signup = mode === 'signup';
  const [message,setMessage] = useState('');
  const [success,setSuccess] = useState(false);
  const [busy,setBusy] = useState(false);
  const [invitationVisible,setInvitationVisible] = useState(false);
  const [invitation,setInvitation] = useState<Invitation|null>(null);
  const [invitationToken,setInvitationToken] = useState<string|null>(null);
  const [created,setCreated] = useState(false);
  const [partialLogin,setPartialLogin] = useState(false);
  const [signinEmail,setSigninEmail] = useState('');
  const notify=(text:string,ok=false)=>{setMessage(text);setSuccess(ok)};
  async function inspect(value:string) {
    const token = parseInvitation(value);
    const info = await authRequest<Invitation>('/invitations/inspect',{token});
    setInvitationToken(token);setInvitation(info);setInvitationVisible(false);setMessage('');
  }
  useEffect(()=>{
    let active=true;
    const token = signup ? new URLSearchParams(location.hash.slice(1)).get('token') : sessionStorage.getItem('gazal_pending_invite');
    if (!token) return;
    if (signup) history.replaceState(null,'',location.pathname);
    let parsed:string;
    try {parsed=parseInvitation(token)}catch(e){notify((e as Error).message);return}
    authRequest<Invitation>('/invitations/inspect',{token:parsed}).then(info=>{
      if(!active)return;
      if(signup){setInvitationToken(parsed);setInvitation(info)}
      else{setSigninEmail(info.email);notify('Sign in with your invited email to join '+info.account+'.',true)}
    }).catch(e=>{if(active){if(!signup)sessionStorage.removeItem('gazal_pending_invite');notify(e.message)}});
    return ()=>{active=false};
  },[signup]);
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();setMessage('');
    const data = new FormData(event.currentTarget);
    if(signup&&data.get('signupPassword')!==data.get('signupConfirm')){notify('The passwords do not match.');return}
    setBusy(true);
    try {
      if(signup){
        const password=String(data.get('signupPassword'));
        if(invitationToken)await authRequest('/invitations/accept',{token:invitationToken,password});
        else await authRequest('/signup',{name:String(data.get('signupName')).trim(),email:String(data.get('signupEmail')).trim(),password});
        setCreated(true);notify('Your account is ready. Sign in to open your workspace.',true);
      } else {
        const result=await authRequest<{token:string}>('/login',{email:String(data.get('signinEmail')).trim(),password:data.get('signinPassword')});
        sessionStorage.setItem('pt_token',result.token);
        const token=sessionStorage.getItem('gazal_pending_invite');
        if(token){
          try{await authRequest('/invitations/accept',{token});sessionStorage.removeItem('gazal_pending_invite')}
          catch(e){if(e instanceof ApiError&&e.status===410)sessionStorage.removeItem('gazal_pending_invite');setPartialLogin(true);notify('Signed in, but the invitation could not be accepted: '+(e as Error).message);return}
        }
        location.assign('/app');
      }
    } catch(e){notify((e as Error).message)} finally{setBusy(false)}
  }
  async function invitationSubmit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const data=new FormData(event.currentTarget);setBusy(true);
    try{await inspect(String(data.get('invitationLink')))}catch(e){notify((e as Error).message)}finally{setBusy(false)}
  }
  return <div className="auth-shell"><aside className="brand-panel"><a href="/" className="brand"><img src="/static/brand/gazal-logo-light.svg" alt="GAZAL." className="gazal-wordmark"/></a><div className="brand-copy"><span className="eyebrow">YOUR TEAM, IN SYNC</span><h1>Good work.<br/>Clear progress.<br/><span>One workspace.</span></h1><p>Bring your people, projects and business growth together—wherever your team works.</p><div className="preview-card"><div className="card-top"><span className="card-icon">◎</span><div><strong>Everything moving forward</strong><small>A clearer view of your workday</small></div><span className="status-dot"/></div>{[['✓','Tasks & project delivery'],['◷','Remote work & team updates'],['↗','Product traction & growth']].map(([icon,text])=><div key={text} className="card-line"><span className="line-icon">{icon}</span><span>{text}</span><span className="check">✓</span></div>)}</div></div><footer>Built for teams that work together, from anywhere.</footer></aside>
    <main className="form-panel"><div className="top-links"><span>{signup?'Already have an account?':'New to your workspace?'}</span><a href={signup?'/signin':'/signup'}>{signup?'Sign in ↗':'Create an account ↗'}</a></div><div className="form-content"><span className="mobile-brand"><img src="/static/brand/gazal-logo.svg" alt="GAZAL." className="gazal-wordmark"/></span>
    {signup?<section><span className="eyebrow dark">JOIN YOUR TEAM</span><h2>Create your account.</h2><p className="subtitle">Create your Gazal account, then join your team’s workspace.</p>
      {!created&&<><button type="button" className="invitation-link" onClick={()=>setInvitationVisible(!invitationVisible)}>Have an invitation? Use it here →</button>
      {invitationVisible&&<form onSubmit={invitationSubmit}><label htmlFor="invitationLink">Invitation link or code</label><input id="invitationLink" name="invitationLink" required autoComplete="off" placeholder="Paste the invitation from your admin"/><button className="primary" disabled={busy}>Continue →</button></form>}
      {invitation&&<div className="invite-summary"><strong>{invitation.account}</strong>{invitation.project&&<p>{invitation.project}</p>}<p>Invited as {(invitation.role||'employee').replaceAll('_',' ')}</p></div>}
      {invitation?.existing_user?<div className="invite-summary"><strong>You already have a Gazal account.</strong><p>Sign in with the invited email address to accept this invitation.</p><button className="primary" onClick={()=>{if(invitationToken)sessionStorage.setItem('gazal_pending_invite',invitationToken);location.assign('/signin')}}>Sign in & join →</button></div>:<form onSubmit={submit} key={invitationToken||'public'}>
        <label htmlFor="signupName">Full name</label><input id="signupName" name="signupName" required minLength={2} maxLength={120} autoComplete="name" defaultValue={invitation?.name||''} readOnly={!!invitation}/>
        <label htmlFor="signupEmail">Work email</label><input id="signupEmail" name="signupEmail" type="email" required autoComplete="username" defaultValue={invitation?.email||''} readOnly={!!invitation}/>
        <Password id="signupPassword" label="Create password" signup/><Password id="signupConfirm" label="Confirm password" signup/>
        <p className="account-help">Your workspace administrator assigns your access after you join.</p><button className="primary" disabled={busy}>{busy?'Creating account…':'Create account →'}</button>
      </form>}</>}
      {created&&<a className="primary" href="/signin">Continue to sign in →</a>}
      <p className="bottom-note">Already invited? You can join your business account during registration.</p>
    </section>:<section><span className="eyebrow dark">WELCOME BACK</span><h2>Sign in to Gazal.</h2><p className="subtitle">Your team, tasks and workday await.</p><form onSubmit={submit}>
      <label htmlFor="signinEmail">Work email</label><input id="signinEmail" name="signinEmail" type="email" required autoComplete="username" placeholder="you@company.com" value={signinEmail} onChange={e=>setSigninEmail(e.target.value)}/>
      <Password id="signinPassword" label="Password"/><div className="account-help">Need access or a password reset? Contact your workspace admin.</div><button className="primary" disabled={busy}>{busy?'Signing in…':'Sign in →'}</button>
    </form><p className="bottom-note">Your access is determined by your assigned workspace role.</p></section>}
    {message&&<div id="authMessage" role="status" aria-live="polite" className={success?'success':''}>{message}{partialLogin&&<p><a href="/app">Open your workspace</a></p>}</div>}
    </div><footer className="form-footer">Gazal · Work & growth, connected.</footer></main>
  </div>;
}
