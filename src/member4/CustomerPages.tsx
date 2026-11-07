import { useEffect, useRef, useState } from 'react';
import { Badge, Button, Empty, Field, Modal, PageHead, SearchBox } from '../components';
import { api, useAuth } from '../member2';
import { Failure, ProjectDetailsContent } from '../member3/Projects';
import { placeholderImage, type Category } from '../member3/types';
import type { CustomerProject, SaveResult } from './types';
import './customer.css';

type Navigation = { go: (path: string) => void };

function useRefreshOnFocus(refresh: () => void) {
  useEffect(() => {
    const visible = () => { if (document.visibilityState === 'visible') refresh(); };
    window.addEventListener('focus', refresh); document.addEventListener('visibilitychange', visible);
    return () => { window.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', visible); };
  }, [refresh]);
}

export function SaveFavouriteButton({ project, onSaved, go }: { project: CustomerProject; onSaved: (project: CustomerProject) => void } & Navigation) {
  const { session, loading } = useAuth();
  const [busy, setBusy] = useState(false), [error, setError] = useState<unknown>(null), [message, setMessage] = useState('');
  const pending = useRef(false);
  if (loading) return <span role="status">Checking sign-in…</span>;
  if (!session) return <Button onClick={() => go('/login')}>Log in to save</Button>;
  if (session.role !== 'customer' || !session.permissions.includes('projects:discover')) return <small className="favourite-restricted">Sign in as Customer to save</small>;
  return <div className="favourite-action"><Button kind={project.saved ? '' : 'primary'} disabled={busy || project.saved} onClick={async () => {
    if (pending.current || project.saved) return;
    pending.current = true; setBusy(true); setError(null); setMessage('');
    try {
      const result = await api<SaveResult>('/favourites', 'POST', { projectId: project.projectId });
      onSaved(result.project); setMessage(result.created ? 'Added to favourites.' : 'Already saved.');
    } catch (failure) { setError(failure); }
    finally { pending.current = false; setBusy(false); }
  }}>{busy ? 'Saving…' : project.saved ? 'Saved' : 'Add to Favourites'}</Button>
    <Failure error={error}/>{message && <small className="favourite-status-msg" role="status">{message}</small>}
  </div>;
}

export function CustomerDetailDialog({ id, go, onClose, onSaved }: { id: string; onClose: () => void; onSaved: (p: CustomerProject) => void } & Navigation) {
  const { session, loading: authLoading } = useAuth();
  const event = useRef({ id, value: crypto.randomUUID() });
  if (event.current.id !== id) event.current = { id, value: crypto.randomUUID() };
  const [project, setProject] = useState<CustomerProject | null>(null), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0);
  useEffect(() => {
    if (authLoading) return;
    const abort = new AbortController(); setProject(null); setError(null);
    const path = `/catalog/projects/${encodeURIComponent(id)}`;
    const detail = session?.role === 'customer' && session.permissions.includes('projects:discover')
      ? api<{ project: CustomerProject }>(`${path}/views`, 'POST', { eventId: event.current.value }, abort.signal).then(result => result.project)
      : api<CustomerProject>(path, 'GET', undefined, abort.signal);
    detail
      .then(data => { if (!abort.signal.aborted) setProject(data); }).catch(failure => { if (!abort.signal.aborted) setError(failure); });
    return () => abort.abort();
  }, [id, session?.account.accountId, authLoading, revision]);
  return <Modal title="Project Details" wide onClose={onClose} footer={<Button onClick={onClose}>Close</Button>}>
    {error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : !project ? <p role="status">Loading project…</p> : <>
      <ProjectDetailsContent project={project}/><div className="page-actions"><SaveFavouriteButton project={project} go={go} onSaved={updated => { setProject(updated); onSaved(updated); }}/></div>
    </>}
  </Modal>;
}

function CustomerProjectCard({ project, go, open, onSaved }: { project: CustomerProject; open: () => void; onSaved: (p: CustomerProject) => void } & Navigation) {
  return <article className="project-card"><div className="card-image"><button className="image-open" aria-label={`View ${project.title}`} onClick={open}><img src={project.images[0]?.url ?? placeholderImage} alt={project.images.length ? project.title : 'Project image placeholder'}/></button><span className="image-label">{project.status}</span></div>
    <div className="card-content"><div className="card-meta"><span>{project.categoryName}</span><span>{project.style}</span></div><button className="card-title" onClick={open}>{project.title}</button><p>{project.description}</p><div className="studio-row">{project.companyName ?? project.designerName}</div>
      <div className="card-bottom">
        <Badge>{project.status}</Badge>
        <div className="card-actions">
          <Button onClick={open}>View Details</Button>
          <SaveFavouriteButton project={project} go={go} onSaved={onSaved}/>
        </div>
      </div>
    </div></article>;
}

export function CustomerCatalog({ go }: Navigation) {
  const { session } = useAuth();
  const [query, setQuery] = useState(''), [categoryId, setCategoryId] = useState(''), [style, setStyle] = useState('');
  const [categories, setCategories] = useState<Category[]>([]), [styles, setStyles] = useState<string[]>([]);
  const [projects, setProjects] = useState<CustomerProject[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const refresh = useRef(() => setRevision(v => v + 1)).current;
  useRefreshOnFocus(refresh);
  useEffect(() => {
    const abort = new AbortController(); setLoading(true); setError(null);
    const params = new URLSearchParams({ q: query, categoryId, style });
    const timer = setTimeout(() => {
      Promise.all([api<CustomerProject[]>(`/catalog/projects?${params}`, 'GET', undefined, abort.signal), api<Category[]>('/project-categories', 'GET', undefined, abort.signal), api<string[]>('/catalog/styles', 'GET', undefined, abort.signal)])
        .then(([rows, options, availableStyles]) => { if (!abort.signal.aborted) { setProjects(rows); setCategories(options); setStyles(availableStyles); } })
        .catch(failure => { if (!abort.signal.aborted) setError(failure); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    }, query ? 200 : 0);
    return () => { clearTimeout(timer); abort.abort(); };
  }, [query, categoryId, style, session?.account.accountId, revision]);
  function saved(project: CustomerProject) { setProjects(rows => rows.map(row => row.projectId === project.projectId ? project : row)); }
  function reset() { setQuery(''); setCategoryId(''); setStyle(''); }
  return <main className="public-main"><section className="hero" style={{ backgroundImage: `linear-gradient(90deg,rgba(29,26,23,.7),rgba(29,26,23,.2)),url(${placeholderImage})` }}><div className="hero-inner"><span className="hero-eyebrow">Curated Architectural Exchange</span><h1>Find the right designer<br/>for your space.</h1><p>Explore current and completed interior design projects.</p><a className="button sand" href="#projects">Explore Projects</a></div></section>
    <section className="discovery-section" id="projects"><div className="section-heading"><div><span className="section-eyebrow">Design Portfolios</span><h2>Design Architecture Showcase</h2><p>Explore projects shared by active interior designers.</p></div></div>
      <div className="customer-filters"><SearchBox value={query} onChange={setQuery} placeholder="Search projects by title, description or style..."/>
        <Field label="Category"><select aria-label="Category" value={categoryId} onChange={event => setCategoryId(event.target.value)}><option value="">All categories</option>{categories.map(c => <option key={c.categoryId} value={c.categoryId}>{c.name}{c.status === 'Suspended' ? ' (inactive)' : ''}</option>)}{categoryId && !categories.some(c => c.categoryId === categoryId) && <option value={categoryId}>Unavailable category</option>}</select></Field>
        <Field label="Style"><select aria-label="Style" value={style} onChange={event => setStyle(event.target.value)}><option value="">All styles</option>{styles.map(s => <option value={s} key={s}>{s}</option>)}{style && !styles.includes(style) && <option value={style}>{style} (unavailable)</option>}</select></Field>
        <Button disabled={!query && !categoryId && !style} onClick={reset}>Reset Filters</Button>
      </div>
      {loading ? <p role="status">Loading projects…</p> : error ? <Failure error={error} retry={refresh}/> : !projects.length ? <Empty title={query || categoryId || style ? 'No matching projects found' : 'No projects available yet'} message="Try another keyword, reset the filters, or return when designers have added projects."/> : <div className="project-grid">{projects.map(project => <CustomerProjectCard key={project.projectId} project={project} go={go} open={() => setSelected(project.projectId)} onSaved={saved}/>)}</div>}
    </section>{selected && <CustomerDetailDialog id={selected} go={go} onClose={() => setSelected(null)} onSaved={saved}/>}</main>;
}

export function FavouriteList({ go }: Navigation) {
  const { session } = useAuth();
  const [query, setQuery] = useState(''), [projects, setProjects] = useState<CustomerProject[]>([]);
  const [loading, setLoading] = useState(true), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0), [selected, setSelected] = useState<string | null>(null);
  const refresh = useRef(() => setRevision(v => v + 1)).current;
  useRefreshOnFocus(refresh);
  useEffect(() => {
    const abort = new AbortController(); setLoading(true); setError(null);
    const timer = setTimeout(() => { api<CustomerProject[]>(`/favourites?q=${encodeURIComponent(query)}`, 'GET', undefined, abort.signal)
      .then(rows => { if (!abort.signal.aborted) setProjects(rows); }).catch(failure => { if (!abort.signal.aborted) setError(failure); }).finally(() => { if (!abort.signal.aborted) setLoading(false); }); }, query ? 200 : 0);
    return () => { clearTimeout(timer); abort.abort(); };
  }, [query, revision, session?.account.accountId]);
  function saved(project: CustomerProject) { setProjects(rows => rows.map(row => row.projectId === project.projectId ? project : row)); }
  return <><PageHead eyebrow="Your Shortlist" title="My Favourites" description="Projects saved to your customer account."/>
    <SearchBox value={query} onChange={setQuery} placeholder="Search your favourites by keyword..."/>
    {loading ? <p role="status">Loading favourites…</p> : error ? <Failure error={error} retry={refresh}/> : !projects.length ? <Empty title={query ? 'No matching favourites' : 'No favourites yet'} message={query ? 'Try another keyword or clear the search.' : 'Browse projects and add the ones you want to save.'} action={!query ? <Button onClick={() => go('/')}>Discover Projects</Button> : undefined}/> : <div className="project-grid">{projects.map(project => <CustomerProjectCard key={project.projectId} project={project} go={go} open={() => setSelected(project.projectId)} onSaved={saved}/>)}</div>}
    {selected && <CustomerDetailDialog id={selected} go={go} onClose={() => setSelected(null)} onSaved={saved}/>}</>;
}
