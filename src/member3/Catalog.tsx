import { useEffect, useState } from 'react';
import { Badge, Button, Empty, Field, Note, PageHead, SearchBox, Table } from '../components';
import { api } from '../member2';
import { Failure, ProjectDetailsDialog } from './Projects';
import { collection, placeholderImage, type Category, type ProjectRecord } from './types';

export function ProjectCatalog() {
  const [query, setQuery] = useState(''), [categoryId, setCategoryId] = useState(''), [categories, setCategories] = useState<Category[]>([]);
  const [projects, setProjects] = useState<ProjectRecord[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    const abort = new AbortController(); setLoading(true); setError(null);
    const timer = setTimeout(() => { Promise.all([api<ProjectRecord[]>(`/catalog/projects?q=${encodeURIComponent(query)}&categoryId=${encodeURIComponent(categoryId)}`, 'GET', undefined, abort.signal), api<Category[]>('/project-categories', 'GET', undefined, abort.signal)])
      .then(([rows, options]) => { if (!abort.signal.aborted) { setProjects(rows); setCategories(options); } }).catch(failure => { if (!abort.signal.aborted) setError(failure); }).finally(() => { if (!abort.signal.aborted) setLoading(false); }); }, query ? 200 : 0);
    return () => { clearTimeout(timer); abort.abort(); };
  }, [query, categoryId, revision]);
  return <main className="public-main"><section className="hero" style={{ backgroundImage: `linear-gradient(90deg,rgba(29,26,23,.7),rgba(29,26,23,.2)),url(${placeholderImage})` }}><div className="hero-inner"><span className="hero-eyebrow">Curated Architectural Exchange</span><h1>Find the right designer<br/>for your space.</h1><p>Explore current and completed interior design projects.</p><a className="button sand" href="#projects">Explore Projects</a></div></section>
    <section className="discovery-section" id="projects"><div className="section-heading"><div><span className="section-eyebrow">Design Portfolios</span><h2>Design Architecture Showcase</h2><p>Explore projects shared by active interior designers.</p></div></div>
      <div className="catalog-filters"><SearchBox value={query} onChange={setQuery} placeholder="Search projects by title, description or style..."/><Field label="Category"><select value={categoryId} onChange={event => setCategoryId(event.target.value)}><option value="">All categories</option>{categories.map(c => <option key={c.categoryId} value={c.categoryId}>{c.name}{c.status === 'Suspended' ? ' (inactive)' : ''}</option>)}</select></Field></div>
      {loading ? <p role="status">Loading projects…</p> : error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : !projects.length ? <Empty title={query || categoryId ? 'No matching projects found' : 'No projects available yet'} message="Try another keyword or come back when designers have added projects."/> : <div className="project-grid">{projects.map(project => <article className="project-card" key={project.projectId}>
        <div className="card-image"><button className="image-open" aria-label={`View ${project.title}`} onClick={() => setSelected(project.projectId)}><img src={project.images[0]?.url ?? placeholderImage} alt={project.images.length ? project.title : 'Project image placeholder'}/></button><span className="image-label">{project.status}</span></div>
        <div className="card-content"><div className="card-meta"><span>{project.categoryName}</span><span>{project.style}</span></div><button className="card-title" onClick={() => setSelected(project.projectId)}>{project.title}</button><p>{project.description}</p><div className="studio-row">{project.companyName ?? project.designerName}</div><div className="card-bottom"><Badge>{project.status}</Badge><Button onClick={() => setSelected(project.projectId)}>View Details</Button></div></div>
      </article>)}</div>}
    </section>{selected && <ProjectDetailsDialog id={selected} onClose={() => setSelected(null)}/>}</main>;
}

export function SharedCategoryList() {
  const [categories, setCategories] = useState<Category[] | null>(null), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0);
  useEffect(() => { const abort = new AbortController(); setError(null); api<Category[]>('/project-categories', 'GET', undefined, abort.signal).then(setCategories).catch(failure => { if (!abort.signal.aborted) setError(failure); }); return () => abort.abort(); }, [revision]);
  return <><PageHead eyebrow="Platform Manager" title="IDP Categories" description="Shared project category source."/>{error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : categories ? <Table heads={['Category ID', 'Category', 'Description', 'Status']}>{categories.map(c => <tr key={c.categoryId}><td>{c.categoryId}</td><td>{c.name}</td><td>{c.description}</td><td>{c.status}</td></tr>)}</Table> : <p role="status">Loading categories…</p>}<Note>Category management belongs to Member 6. This read adapter uses the same category records as designer projects and customer discovery.</Note></>;
}

export function AnalyticsProjectAdapter() {
  const [projects, setProjects] = useState<ProjectRecord[] | null>(null), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0), [selected, setSelected] = useState<ProjectRecord | null>(null);
  useEffect(() => { const abort = new AbortController(); setError(null); Promise.all([api<ProjectRecord[]>(collection('Current'), 'GET', undefined, abort.signal), api<ProjectRecord[]>(collection('Past'), 'GET', undefined, abort.signal)]).then(([current, past]) => { if (!abort.signal.aborted) setProjects([...current, ...past]); }).catch(failure => { if (!abort.signal.aborted) setError(failure); }); return () => abort.abort(); }, [revision]);
  return <><PageHead eyebrow="Interior Designer" title="Project Analytics" description="Project references ready for the activity integration."/>{error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : !projects ? <p role="status">Loading projects…</p> : <Table heads={['Project ID', 'Your project', 'Status', 'Action']} empty={!projects.length}>{projects.map(p => <tr key={p.projectId}><td>{p.projectId}</td><td>{p.title}</td><td>{p.status}</td><td><Button onClick={() => setSelected(p)}>View Project</Button></td></tr>)}</Table>}<Note>Views and shortlists are unavailable until Member 5 connects activity storage. No sample counts are displayed.</Note>{selected && <ProjectDetailsDialog id={selected.projectId} status={selected.status} onClose={() => setSelected(null)}/>}</>;
}
