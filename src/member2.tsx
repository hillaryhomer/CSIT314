import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Button, Details, Empty, Field, Modal, PageHead, SearchBox } from './components';
import type { Role } from './data';

type Session = { account: { accountId: string; username: string }; role: Role; permissions: string[]; csrfToken: string; development?: boolean };
let csrfToken = '';
export class RequestError extends Error {
  constructor(message: string, public fields: Record<string, string> = {}, public code = 'REQUEST_FAILED') { super(message); }
}
export async function api<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { method, credentials: 'same-origin', signal,
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new RequestError('Could not reach the server. Please retry.');
  }
  const data = await response.json().catch(() => { throw new RequestError('The server returned an unreadable response.'); });
  if (!response.ok) {
    if (response.status === 401 || data.error?.message?.includes('assigned profile cannot access')) window.dispatchEvent(new Event('session-ended'));
    throw new RequestError(data.error?.message ?? 'The request failed.', data.error?.fields, data.error?.code);
  }
  return data as T;
}

const Auth = createContext<{ session: Session | null; loading: boolean; error: string; refresh: () => Promise<void>; accept: (s: Session | null) => void }>(null!);
export const useAuth = () => useContext(Auth);
export const roleHome: Record<Role, string> = { admin: '/admin', designer: '/designer', customer: '/', manager: '/manager' };
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  function accept(value: Session | null) { csrfToken = value?.csrfToken ?? ''; setSession(value); }
  async function refresh() {
    try { accept(await api<Session>('/auth/session')); setError(''); }
    catch (failure) { accept(null); setError(failure instanceof Error ? failure.message : 'Unable to check session.'); }
    finally { setLoading(false); }
  }
  useEffect(() => {
    void refresh();
    const ended = () => accept(null);
    const visible = () => { if (document.visibilityState === 'visible') void refresh(); };
    window.addEventListener('session-ended', ended);
    window.addEventListener('focus', refresh);
    window.addEventListener('pageshow', refresh);
    document.addEventListener('visibilitychange', visible);
    return () => { window.removeEventListener('session-ended', ended); window.removeEventListener('focus', refresh); window.removeEventListener('pageshow', refresh); document.removeEventListener('visibilitychange', visible); };
  }, []);
  return <Auth.Provider value={{ session, loading, error, refresh, accept }}>{children}</Auth.Provider>;
}

export function Access({ role, children, go }: { role: Role; children: ReactNode; go: (path: string) => void }) {
  const { session, loading, refresh, error } = useAuth();
  useEffect(() => { void refresh(); }, [role]);
  if (loading) return <p role="status">Checking session…</p>;
  if (!session) return <div className="form-card"><h1>Sign in required</h1><p role="alert">{error || 'Your session has ended. Sign in to continue.'}</p><Button kind="primary" onClick={() => go('/login')}>Log In</Button><Button onClick={() => void refresh()}>Retry</Button></div>;
  if (session.role !== role) return <div className="form-card"><h1>Access denied</h1><p>Your account does not have access to this workspace.</p><Button onClick={() => go(roleHome[session.role])}>My dashboard</Button></div>;
  return <>{children}</>;
}

function Failure({ error }: { error: unknown }) { return error ? <p className="admin-error" role="alert">{error instanceof Error ? error.message : String(error)}</p> : null; }

export function LoginForm({ go }: { go: (path: string) => void }) {
  const { accept } = useAuth();
  const [identifier, setIdentifier] = useState(''); const [password, setPassword] = useState('');
  const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  return <main className="login-page"><div className="login-photo" style={{ backgroundImage: "url('/images/interior-1.jpg')" }}/><div className="login-content"><Button onClick={() => go('/')}>Back to Discover</Button><h1>Welcome back</h1><p>Sign in to your workspace.</p><form className="form-stack" onSubmit={async e => {
    e.preventDefault(); if (pending.current) return; pending.current = true; setBusy(true); setError(null);
    try { const s = await api<Session>('/auth/login', 'POST', { identifier, password }); accept(s); setPassword(''); go(roleHome[s.role]); }
    catch (failure) { setError(failure); } finally { pending.current = false; setBusy(false); }
  }}><Failure error={error}/><Field label="Username or email"><input required autoComplete="username" value={identifier} maxLength={254} onChange={e => setIdentifier(e.target.value)}/></Field><Field label="Password"><input required type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)}/></Field><Button type="submit" kind="primary" disabled={busy}>{busy ? 'Signing in…' : 'Log In'}</Button></form></div></main>;
}

export function LogoutForm({ go }: { go: (path: string) => void }) {
  const { session, accept } = useAuth(); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  return <main className="logout-page"><div className="logout-card"><h1>End your session?</h1><p>{session?.development ? 'Development mode uses a fixed server identity. Restart without --dev to use real login and logout.' : 'Sign out of this browser session.'}</p><Failure error={error}/><div className="page-actions"><Button disabled={busy} onClick={() => go(session ? roleHome[session.role] : '/')}>Cancel</Button><Button kind="primary" disabled={busy || !!session?.development} onClick={async () => {
    setBusy(true); setError(null);
    try { if (session) await api('/auth/logout', 'POST', {}); accept(null); go('/login'); }
    catch (failure) {
      if (failure instanceof RequestError && failure.code === 'UNAUTHENTICATED') { accept(null); go('/login'); }
      else setError(failure);
    } finally { setBusy(false); }
  }}>{busy ? 'Signing out…' : 'Log Out'}</Button></div></div></main>;
}

type CompanyData = { companyId: string; ownerId: string; name: string; regNumber: string; address: string; contact: string; description: string };
type CompanyInput = Omit<CompanyData, 'companyId' | 'ownerId'>;
const blank: CompanyInput = { name: '', regNumber: '', address: '', contact: '', description: '' };
export function CompanyManagement({ notify }: { notify: (message: string) => void }) {
  const [company, setCompany] = useState<CompanyData | null>(null), [query, setQuery] = useState('');
  const [matches, setMatches] = useState(false), [loading, setLoading] = useState(true), [revision, setRevision] = useState(0);
  const [mode, setMode] = useState<'view' | 'create' | 'edit' | 'delete'>('view');
  const [form, setForm] = useState<CompanyInput>(blank), [error, setError] = useState<unknown>(null), [busy, setBusy] = useState(false);
  const pending = useRef(false);
  useEffect(() => {
    const abort = new AbortController(); setLoading(true); setError(null);
    const timer = setTimeout(() => {
      api<{ company: CompanyData | null; matches: boolean }>(`/company?q=${encodeURIComponent(query)}`, 'GET', undefined, abort.signal)
        .then(data => { if (!abort.signal.aborted) { setCompany(data.company); setMatches(data.matches); } })
        .catch(failure => { if (!abort.signal.aborted) setError(failure); })
        .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    }, query ? 200 : 0);
    return () => { clearTimeout(timer); abort.abort(); };
  }, [query, revision]);
  async function save() {
    if (pending.current) return; pending.current = true; setBusy(true); setError(null);
    try {
      if (mode === 'delete') { await api(`/company/${company!.companyId}`, 'DELETE', {}); setCompany(null); }
      else { setCompany(await api<CompanyData>(mode === 'create' ? '/company' : `/company/${company!.companyId}`, mode === 'create' ? 'POST' : 'PUT', form)); }
      notify(mode === 'delete' ? 'Company deleted successfully.' : 'Company saved successfully.'); setMode('view'); setRevision(v => v + 1);
    } catch (failure) { setError(failure); } finally { pending.current = false; setBusy(false); }
  }
  const fields = error instanceof RequestError ? error.fields : {};
  const cancel = () => { setMode('view'); setError(null); };
  return <><PageHead eyebrow="Interior Designer" title="Company Information" description="Manage your studio's business information."/>
    {mode !== 'delete' && <Failure error={error}/>}
    {(mode === 'create' || mode === 'edit') ? <form className="form-card form-stack" onSubmit={e => { e.preventDefault(); void save(); }}><fieldset disabled={busy} className="admin-form-fields">
      {(['name', 'regNumber', 'address', 'contact', 'description'] as const).map(key => <Field key={key} label={{ name: 'Company name', regNumber: 'Business registration number (optional)', address: 'Business address', contact: 'Contact details', description: 'Description' }[key]} required={['name', 'address', 'contact'].includes(key)}>
        {key === 'description' ? <textarea rows={4} value={form[key]} maxLength={4000} aria-describedby={fields[key] ? `company-${key}-error` : undefined} onChange={e => setForm({ ...form, [key]: e.target.value })}/> : <input required={['name', 'address', 'contact'].includes(key)} value={form[key]} maxLength={{ name: 120, regNumber: 80, address: 500, contact: 254 }[key]} aria-invalid={!!fields[key]} aria-describedby={fields[key] ? `company-${key}-error` : undefined} onChange={e => setForm({ ...form, [key]: e.target.value })}/>}
        {fields[key] && <small id={`company-${key}-error`}>{fields[key]}</small>}
      </Field>)}
      </fieldset><div className="form-actions"><Button disabled={busy} onClick={cancel}>Cancel</Button><Button type="submit" kind="primary" disabled={busy}>{busy ? 'Saving…' : 'Save Company'}</Button></div></form>
      : <><SearchBox value={query} onChange={setQuery} placeholder="Search your company information..."/>
        {loading ? <p role="status">Loading company…</p> : error ? <Button onClick={() => setRevision(v => v + 1)}>Retry</Button> : !company ? <Empty title="No company information yet" message="Create your company's information to get started." action={<Button kind="primary" onClick={() => { setForm(blank); setMode('create'); }}>Create Company</Button>}/> : <>
          {matches ? <Details rows={[['Company name', company.name], ['Registration number', company.regNumber || '—'], ['Address', company.address], ['Contact', company.contact], ['Description', company.description || '—']]}/> : <Empty title="No matching company information" message="Try a different keyword."/>}
          <div className="page-actions"><Button kind="primary" onClick={() => { const { name, regNumber, address, contact, description } = company; setForm({ name, regNumber, address, contact, description }); setMode('edit'); }}>Edit Company</Button><Button kind="danger" onClick={() => setMode('delete')}>Delete Company</Button></div>
        </>}
      </>}
    {mode === 'delete' && <Modal title="Delete company information?" busy={busy} onClose={cancel} footer={<><Button disabled={busy} onClick={cancel}>Cancel</Button><Button kind="danger" disabled={busy} onClick={() => void save()}>{busy ? 'Deleting…' : 'Delete Company'}</Button></>}><Failure error={error}/><p>Delete <strong>{company?.name}</strong>? Your account and project records will be preserved.</p></Modal>}
  </>;
}
