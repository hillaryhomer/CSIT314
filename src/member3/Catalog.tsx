import { useEffect, useState } from 'react';
import { Button, Note, PageHead, Table } from '../components';
import { api } from '../member2';
import { Failure, ProjectDetailsDialog } from './Projects';

export { CustomerCatalog as ProjectCatalog } from '../member4/CustomerPages';

type Analytics = { projectId: string; title: string; status: 'Current' | 'Past'; views: number; shortlists: number };
export function AnalyticsProjectAdapter() {
  const [projects, setProjects] = useState<Analytics[] | null>(null), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<Analytics | null>(null);
  useEffect(() => {
    const abort = new AbortController(); setProjects(null); setError(null);
    api<Analytics[]>('/designer/analytics', 'GET', undefined, abort.signal).then(rows => { if (!abort.signal.aborted) setProjects(rows); }).catch(failure => { if (!abort.signal.aborted) setError(failure); });
    return () => abort.abort();
  }, [revision]);
  useEffect(() => { const refresh = () => setRevision(v => v + 1); window.addEventListener('focus', refresh); return () => window.removeEventListener('focus', refresh); }, []);
  return <><PageHead eyebrow="Interior Designer" title="Project Analytics" description="Customer detail views and currently saved favourites for your projects."/>
    <Button onClick={() => setRevision(v => v + 1)}>Refresh counts</Button>
    {error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : !projects ? <p role="status">Loading analytics...</p> : <Table heads={['Project ID', 'Your project', 'Status', 'Views', 'Shortlists', 'Action']} empty={!projects.length}>{projects.map(p => <tr key={p.projectId}><td>{p.projectId}</td><td>{p.title}</td><td>{p.status}</td><td>{p.views}</td><td>{p.shortlists}</td><td><Button onClick={() => setSelected(p)}>View Project</Button></td></tr>)}</Table>}
    <Note>Views count successful customer detail openings, including repeat visits. Shortlists count unique saved customer-project relationships.</Note>
    {selected && <ProjectDetailsDialog id={selected.projectId} status={selected.status} onClose={() => setSelected(null)}/>}</>;
}
