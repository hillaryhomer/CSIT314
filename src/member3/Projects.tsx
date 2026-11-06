import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Badge, Button, Details, Empty, Modal, Note, PageHead, SearchBox, Table } from '../components';
import { api, RequestError } from '../member2';
import { collection, placeholderImage, type Category, type DraftImage, type ProjectInput, type ProjectRecord, type ProjectStatus } from './types';

export function Failure({ error, retry }: { error: unknown; retry?: () => void }) {
  return error ? <div role="alert" className="admin-error"><p>{error instanceof Error ? error.message : 'The request failed. Please retry.'}</p>{retry && <Button onClick={retry}>Retry</Button>}</div> : null;
}

export function ProjectDetailsContent({ project }: { project: Omit<ProjectRecord, 'ownerAccountId' | 'companyId'> }) {
  return <div className="project-detail-content"><div className="project-gallery">
    {project.images.length ? project.images.map((image, i) => <img key={image.imageId} src={image.url} alt={`${project.title}, image ${i + 1}`}/>) : <p className="inline-note">No project images uploaded.</p>}
    </div><h2>{project.title}</h2><Badge>{project.status}</Badge><p className="project-description">{project.description}</p>
    <Details rows={[
      ['Project ID', project.projectId], ['Company / designer', project.companyName ?? project.designerName],
      ['Category', project.categoryName + (project.categoryStatus === 'Suspended' ? ' (inactive)' : '')],
      ['Style', project.style], ['Created', new Date(project.createdAt).toLocaleString()], ['Updated', new Date(project.updatedAt).toLocaleString()],
    ]}/></div>;
}

export function ProjectDetailsDialog({ id, status, onClose }: { id: string; status?: ProjectStatus; onClose: () => void }) {
  const [project, setProject] = useState<ProjectRecord | null>(null), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0);
  useEffect(() => {
    const abort = new AbortController(); setProject(null); setError(null);
    api<ProjectRecord>(status ? `${collection(status)}/${id}` : `/catalog/projects/${id}`, 'GET', undefined, abort.signal)
      .then(data => { if (!abort.signal.aborted) setProject(data); }).catch(failure => { if (!abort.signal.aborted) setError(failure); });
    return () => abort.abort();
  }, [id, status, revision]);
  return <Modal title="Project Details" wide onClose={onClose} footer={<Button onClick={onClose}>Close</Button>}>
    {error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : project ? <ProjectDetailsContent project={project}/> : <p role="status">Loading project…</p>}
  </Modal>;
}

type Dialog = { action: 'create' | 'edit' | 'delete'; id?: string };
export function ProjectManagement({ status, go, notify }: { status: ProjectStatus; go: (path: string) => void; notify: (message: string) => void }) {
  const [query, setQuery] = useState(''), [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(true), [error, setError] = useState<unknown>(null), [revision, setRevision] = useState(0);
  const [dialog, setDialog] = useState<Dialog | null>(null), [viewId, setViewId] = useState<string | null>(null);
  useEffect(() => {
    const abort = new AbortController(); setLoading(true); setError(null);
    const timer = setTimeout(() => { api<ProjectRecord[]>(`${collection(status)}?q=${encodeURIComponent(query)}`, 'GET', undefined, abort.signal)
      .then(data => { if (!abort.signal.aborted) setProjects(data); })
      .catch(failure => { if (!abort.signal.aborted) setError(failure); }).finally(() => { if (!abort.signal.aborted) setLoading(false); }); }, query ? 200 : 0);
    return () => { clearTimeout(timer); abort.abort(); };
  }, [status, query, revision]);
  return <><PageHead eyebrow="Portfolio" title={`${status} Projects`} description="Manage your design projects and their images."
    action={<div className="tabs">{(['Current', 'Past'] as const).map(s => <button className={s === status ? 'selected' : ''} key={s} onClick={() => go(`/designer/${s.toLowerCase()}`)}>{s}</button>)}</div>}/>
    <SearchBox value={query} onChange={setQuery} placeholder={`Search ${status.toLowerCase()} projects by keyword...`} action={<Button kind="primary" onClick={() => setDialog({ action: 'create' })}>Add Project</Button>}/>
    {loading ? <p role="status">Loading projects…</p> : error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : !projects.length ? <Empty title={query ? 'No matching projects' : `No ${status.toLowerCase()} projects yet`} message={query ? 'Try another keyword.' : 'Add your first project to start your portfolio.'}/> :
      <Table heads={['Project', 'Category / style', 'Status', 'Actions']}>{projects.map(project => <tr key={project.projectId}>
        <td><div className="project-cell"><img src={project.images[0]?.url ?? placeholderImage} alt={project.images.length ? project.title : 'Project image placeholder'}/><div><strong>{project.title}</strong><small className="project-id">{project.projectId}</small></div></div></td>
        <td>{project.categoryName} / {project.style}</td><td><Badge>{project.status}</Badge></td><td><div className="row-actions">
          <button onClick={() => setViewId(project.projectId)}>View</button><button onClick={() => setDialog({ action: 'edit', id: project.projectId })}>Edit</button><button className="danger-link" onClick={() => setDialog({ action: 'delete', id: project.projectId })}>Delete</button>
        </div></td></tr>)}</Table>}
    <Note>Changes are saved to the server. Current and Past projects remain separate; editing does not change their status.</Note>
    {viewId && <ProjectDetailsDialog id={viewId} status={status} onClose={() => setViewId(null)}/>}
    {dialog && <ProjectFormDialog key={`${dialog.action}-${dialog.id ?? 'new'}`} state={dialog} status={status} close={() => setDialog(null)} saved={message => { setDialog(null); notify(message); setRevision(v => v + 1); }}/>}</>;
}

function readImage(file: File): Promise<DraftImage> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 2 * 1024 * 1024) return Promise.reject(new Error('Use JPEG, PNG or WebP files up to 2 MiB each.'));
  return new Promise((resolve, reject) => {
    const reader = new FileReader(); reader.onerror = () => reject(new Error('The image could not be read. Please select it again.'));
    reader.onload = () => { const url = String(reader.result); resolve({ url, data: url.split(',')[1], mimeType: file.type }); }; reader.readAsDataURL(file);
  });
}

function ProjectFormDialog({ state, status, close, saved }: { state: Dialog; status: ProjectStatus; close: () => void; saved: (message: string) => void }) {
  const [project, setProject] = useState<ProjectRecord | null>(null), [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState<ProjectInput>({ title: '', description: '', categoryId: '', style: '' }), [images, setImages] = useState<DraftImage[]>([]);
  const [loading, setLoading] = useState(true), [loadError, setLoadError] = useState<unknown>(null), [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false), [reading, setReading] = useState(false), [revision, setRevision] = useState(0); const pending = useRef(false);
  useEffect(() => {
    const abort = new AbortController(); setLoading(true); setLoadError(null);
    Promise.all([api<Category[]>('/project-categories', 'GET', undefined, abort.signal), state.id ? api<ProjectRecord>(`${collection(status)}/${state.id}`, 'GET', undefined, abort.signal) : Promise.resolve(null)])
      .then(([options, record]) => { if (abort.signal.aborted) return; setCategories(options); setProject(record);
        if (record) { setForm({ title: record.title, description: record.description, categoryId: record.categoryId, style: record.style }); setImages(record.images); } })
      .catch(failure => { if (!abort.signal.aborted) setLoadError(failure); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [state.id, status, revision]);
  async function submit() {
    if (pending.current || reading) return; pending.current = true; setBusy(true); setError(null);
    try {
      if (state.action === 'delete') await api(`${collection(status)}/${state.id}`, 'DELETE', {});
      else await api(state.action === 'create' ? collection(status) : `${collection(status)}/${state.id}`, state.action === 'create' ? 'POST' : 'PUT',
        { ...form, images: images.map(image => image.imageId ? { imageId: image.imageId } : { data: image.data, mimeType: image.mimeType }) });
      saved(`${status} project ${state.action === 'delete' ? 'deleted' : state.action === 'create' ? 'created' : 'updated'} successfully.`);
    } catch (failure) { setError(failure); } finally { pending.current = false; setBusy(false); }
  }
  const fields = error instanceof RequestError ? error.fields : {};
  const input = (key: keyof ProjectInput) => ({ id: `project-${key}`, required: true, value: form[key], 'aria-invalid': !!fields[key], 'aria-describedby': fields[key] ? `project-${key}-error` : undefined, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setForm(value => ({ ...value, [key]: event.target.value })) });
  function field(key: keyof ProjectInput, label: string, control: ReactNode) { return <div className="field"><label htmlFor={`project-${key}`}>{label}</label>{control}{fields[key] && <small className="admin-field-error" id={`project-${key}-error`}>{fields[key]}</small>}</div>; }
  return <Modal title={`${state.action === 'create' ? 'Create' : state.action === 'edit' ? 'Update' : 'Delete'} ${status} Project${state.action === 'delete' ? '?' : ''}`} wide busy={busy || reading} onClose={close}>
    {loading ? <p role="status">Loading project form…</p> : loadError ? <Failure error={loadError} retry={() => setRevision(v => v + 1)}/> : state.action === 'delete' ? <>
      <p>Delete <strong>{project?.title}</strong> ({project?.projectId}) and its uploaded images? Your account, company and other projects will be preserved.</p><Failure error={error}/>
      <div className="form-actions"><Button disabled={busy} onClick={close}>Cancel</Button><Button kind="danger" disabled={busy} onClick={() => void submit()}>{busy ? 'Deleting…' : 'Delete Project'}</Button></div>
    </> : <form className="form-stack" onSubmit={event => { event.preventDefault(); void submit(); }}><Failure error={error}/><fieldset disabled={busy || reading} className="admin-form-fields">
      {field('title', 'Project title', <input {...input('title')} maxLength={160}/>)}
      <div className="field-grid">{field('categoryId', 'Category', <select {...input('categoryId')}><option value="">Select category</option>{categories.filter(c => c.status === 'Active' || c.categoryId === project?.categoryId).map(c => <option key={c.categoryId} value={c.categoryId}>{c.name}{c.status === 'Suspended' ? ' (inactive, current assignment only)' : ''}</option>)}</select>)}
      {field('style', 'Style', <input {...input('style')} maxLength={100}/>)}</div>
      {field('description', 'Project description', <textarea {...input('description')} rows={5} maxLength={6000}/>)}
      <div className="field"><label htmlFor="project-images">Images (optional)</label><input id="project-images" type="file" multiple accept="image/jpeg,image/png,image/webp" aria-describedby="project-image-help" onChange={async event => {
        const files = Array.from(event.target.files ?? []); event.target.value = ''; setError(null);
        if (images.length + files.length > 5) { setError(new Error('Choose up to five images.')); return; }
        setReading(true); try { const added = await Promise.all(files.map(readImage)); setImages(current => [...current, ...added]); } catch (failure) { setError(failure); } finally { setReading(false); }
      }}/><small id="project-image-help">Up to 5 JPEG, PNG or WebP images, 2 MiB and 12 megapixels each. Images are saved only when you submit.</small>
        {fields.images && <small className="admin-field-error" role="alert">{fields.images}</small>}
        <div className="project-upload-list">{images.map((image, i) => <div key={image.imageId ?? i}><img src={image.url} alt={`Project image ${i + 1}`}/><Button onClick={() => setImages(current => current.filter((_, index) => i !== index))}>Remove image {i + 1}</Button></div>)}</div>
      </div></fieldset>{reading && <p role="status">Reading images…</p>}<div className="form-actions"><Button disabled={busy || reading} onClick={close}>Cancel</Button><Button kind="primary" type="submit" disabled={busy || reading}>{busy ? 'Saving…' : 'Save Project'}</Button></div></form>}
  </Modal>;
}
