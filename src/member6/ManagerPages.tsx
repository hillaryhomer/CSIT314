import { useEffect, useRef, useState } from 'react';
import { Button, Details, Empty, Field, Modal, Note, PageHead, SearchBox, Table } from '../components';
import { api, RequestError } from '../member2';
import { Failure } from '../member3/Projects';

type Category = { categoryId: string; name: string; description: string; status: string; createdAt: string | null; updatedAt: string | null };
type Dialog = { action: 'create' | 'view' | 'edit' | 'delete'; id?: string };
const base = '/manager/categories';

export function CategoryManagement() {
  const [query, setQuery] = useState(''), [rows, setRows] = useState<Category[] | null>(null), [error, setError] = useState<unknown>(null);
  const [revision, setRevision] = useState(0), [dialog, setDialog] = useState<Dialog | null>(null), [message, setMessage] = useState('');
  useEffect(() => {
    const abort = new AbortController(); setRows(null); setError(null);
    const timer = setTimeout(() => { api<Category[]>(`${base}?q=${encodeURIComponent(query)}`, 'GET', undefined, abort.signal)
      .then(data => { if (!abort.signal.aborted) setRows(data); }).catch(failure => { if (!abort.signal.aborted) setError(failure); }); }, query ? 200 : 0);
    return () => { clearTimeout(timer); abort.abort(); };
  }, [query, revision]);
  return <><PageHead eyebrow="Platform Manager" title="IDP Categories" description="Manage the categories shared by designer projects and customer discovery."/>
    <SearchBox value={query} onChange={setQuery} placeholder="Search categories by name or description..." action={<Button kind="primary" onClick={() => setDialog({ action: 'create' })}>Add Category</Button>}/>
    {message && <p role="status">{message}</p>}
    {error ? <Failure error={error} retry={() => setRevision(v => v + 1)}/> : !rows ? <p role="status">Loading categories...</p> : !rows.length ? <Empty title={query ? 'No matching categories' : 'No categories yet'} message="Create a category or try another keyword."/> :
      <Table heads={['Category ID', 'Category', 'Description', 'Actions']}>{rows.map(row => <tr key={row.categoryId}><td>{row.categoryId}</td><td>{row.name}</td><td>{row.description}</td><td><div className="row-actions">{(['view', 'edit', 'delete'] as const).map(action => <button key={action} onClick={() => setDialog({ action, id: row.categoryId })}>{action[0]!.toUpperCase() + action.slice(1)}</button>)}</div></td></tr>)}</Table>}
    <Note>Deleted categories remain attached to historical projects but cannot be newly assigned. Deleted names remain reserved.</Note>
    {dialog && <CategoryDialog key={`${dialog.action}-${dialog.id ?? 'new'}`} state={dialog} close={() => setDialog(null)} saved={text => { setDialog(null); setMessage(text); setRevision(v => v + 1); }}/>}</>;
}

function CategoryDialog({ state, close, saved }: { state: Dialog; close: () => void; saved: (message: string) => void }) {
  const [record, setRecord] = useState<Category | null>(null), [name, setName] = useState(''), [description, setDescription] = useState('');
  const [loading, setLoading] = useState(Boolean(state.id)), [loadError, setLoadError] = useState<unknown>(null), [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false), [revision, setRevision] = useState(0); const pending = useRef(false);
  useEffect(() => {
    if (!state.id) return;
    const abort = new AbortController(); setLoading(true); setLoadError(null);
    api<Category>(`${base}/${encodeURIComponent(state.id)}`, 'GET', undefined, abort.signal).then(data => {
      if (!abort.signal.aborted) { setRecord(data); setName(data.name); setDescription(data.description); }
    }).catch(failure => { if (!abort.signal.aborted) setLoadError(failure); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [state.id, revision]);
  const fields = error instanceof RequestError ? error.fields : {};
  async function submit() {
    if (pending.current) return; pending.current = true; setBusy(true); setError(null);
    try {
      await api(state.action === 'create' ? base : `${base}/${encodeURIComponent(state.id!)}`, state.action === 'create' ? 'POST' : state.action === 'edit' ? 'PUT' : 'DELETE', state.action === 'delete' ? {} : { name, description });
      saved(`Category ${state.action === 'create' ? 'created' : state.action === 'edit' ? 'updated' : 'deleted'} successfully.`);
    } catch (failure) { setError(failure); } finally { pending.current = false; setBusy(false); }
  }
  return <Modal title={`${state.action === 'create' ? 'Create' : state.action === 'view' ? 'View' : state.action === 'edit' ? 'Edit' : 'Delete'} Category`} busy={busy} onClose={() => { if (!busy) close(); }} footer={<>
    <Button disabled={busy} onClick={close}>{state.action === 'view' ? 'Close' : 'Cancel'}</Button>
    {state.action !== 'view' && !loading && !loadError && <Button kind={state.action === 'delete' ? 'danger' : 'primary'} disabled={busy} onClick={() => void submit()}>{busy ? 'Saving...' : state.action === 'delete' ? 'Confirm Delete' : 'Save Category'}</Button>}
  </>}>
    {loading ? <p role="status">Loading category...</p> : loadError ? <Failure error={loadError} retry={() => setRevision(v => v + 1)}/> : <>
      <Failure error={error}/>
      {state.action === 'delete' ? <p>Delete category <strong>{record?.name}</strong> ({record?.categoryId})? Existing projects will retain this category.</p> : state.action === 'view' ? <Details rows={[
        ['Category ID', record?.categoryId ?? ''], ['Name', name], ['Description', description], ['Created', record?.createdAt ?? 'Not recorded for legacy category'], ['Updated', record?.updatedAt ?? 'Not recorded for legacy category'],
      ]}/> : <div className="form-stack"><Field label="Category name"><input id="category-name" aria-label="Category name" value={name} maxLength={100} required aria-invalid={Boolean(fields.name)} aria-describedby={fields.name ? 'category-name-error' : undefined} onChange={event => setName(event.target.value)}/>{fields.name && <small id="category-name-error" className="admin-field-error" role="alert">{fields.name}</small>}</Field>
        <Field label="Description"><textarea id="category-description" aria-label="Description" value={description} maxLength={2000} aria-describedby={fields.description ? 'category-desc-error' : undefined} onChange={event => setDescription(event.target.value)}/>{fields.description && <small id="category-desc-error" className="admin-field-error" role="alert">{fields.description}</small>}</Field></div>}
    </>}
  </Modal>;
}

type Report = { period: string; timezone: string; startInclusive: string; endExclusive: string; generatedAt: string; partial: boolean; future: boolean;
  metrics: { projectsCreated: number; viewEvents: number }; coverage: { retainedSince: string; complete: boolean; note: string } };
function today() { return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Makassar', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); }

export function PlatformReports() {
  const [kind, setKind] = useState('daily'), [value, setValue] = useState(today()), [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState<unknown>(null); const pending = useRef(false);
  return <><PageHead eyebrow="Platform Manager" title="Platform Reports" description="Generate reports from recorded project creations and customer view events."/>
    <form className="report-controls" onSubmit={async event => {
      event.preventDefault(); if (pending.current) return; pending.current = true; setBusy(true); setReport(null); setError(null);
      try { setReport(await api<Report>(`/manager/reports/${kind}?period=${encodeURIComponent(value)}`)); }
      catch (failure) { setError(failure); } finally { pending.current = false; setBusy(false); }
    }}>
      <Field label="Report period"><select aria-label="Report period" disabled={busy} value={kind} onChange={event => { const next = event.target.value; setKind(next); setValue(next === 'monthly' ? today().slice(0, 7) : today()); setReport(null); setError(null); }}>{['daily', 'weekly', 'monthly'].map(period => <option key={period} value={period}>{period[0]!.toUpperCase() + period.slice(1)}</option>)}</select></Field>
      <Field label={kind === 'monthly' ? 'Selected month' : kind === 'weekly' ? 'Week reference date' : 'Selected date'}><input aria-label={kind === 'monthly' ? 'Selected month' : kind === 'weekly' ? 'Week reference date' : 'Selected date'} required disabled={busy} type={kind === 'monthly' ? 'month' : 'date'} value={value} min={kind === 'monthly' ? '2000-01' : '2000-01-01'} max={kind === 'monthly' ? '9998-12' : '9998-12-31'} onChange={event => { setValue(event.target.value); setReport(null); }}/></Field>
      <Button type="submit" kind="primary" disabled={busy}>{busy ? 'Generating...' : 'Generate Report'}</Button>
    </form>
    <Failure error={error}/>{busy && <p role="status">Loading report...</p>}
    {report && <div className="report-result"><h2>{report.period[0]!.toUpperCase() + report.period.slice(1)} Report</h2>
      <Details rows={[
        ['Timezone', report.timezone], ['Start (inclusive)', report.startInclusive], ['End (exclusive)', report.endExclusive], ['Generated at', report.generatedAt],
        ['Status', report.future ? 'Future period: no activity yet' : report.partial ? 'Partial: current period is still in progress' : 'Closed calendar period'],
      ]}/>
      {!report.coverage.complete && <p role="alert">Incomplete historical coverage. {report.coverage.note}</p>}
      <p>Continuous retention began: {report.coverage.retainedSince}</p>
      <Table heads={['Recorded activity in period', 'Count']}><tr><td>Projects created</td><td>{report.metrics.projectsCreated}</td></tr><tr><td>Customer view events</td><td>{report.metrics.viewEvents}</td></tr></Table>
    </div>}
    <Note>Weekly periods run Monday to Monday; monthly periods use the full calendar month. Views include repeat visits. Favourite totals are current state and are not presented as historical additions. Counts cover activity recorded up to report generation.</Note>
  </>;
}
