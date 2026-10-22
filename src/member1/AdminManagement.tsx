import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AlertTriangle, Plus } from 'lucide-react';
import { PERMISSION_VALUES, ROLE_VALUES, type AccountView, type Permission, type ProfileInput, type ProfileView } from './types';
import { Badge, Button, Details, Empty, Modal, Note, PageHead, SearchBox, Table } from '../components';
import { ApiClientError, member1Api } from './api';

type Module = 'profiles' | 'accounts';
type RecordView = ProfileView | AccountView;
type DialogState = { action: 'Create' | 'View' | 'Update' | 'Suspend'; recordId?: string };
const roleLabels = { admin: 'User Admin', designer: 'Interior Designer', customer: 'Customer', manager: 'Platform Manager' };
const permissionLabels: Record<Permission, string> = {
  'profiles:read': 'View and search profiles', 'profiles:write': 'Create, update and suspend profiles',
  'accounts:read': 'View accounts', 'accounts:write': 'Create and update accounts',
  'projects:manage': 'Manage projects', 'projects:discover': 'Discover projects',
  'reports:read': 'View reports', 'categories:manage': 'Manage categories',
};
function asFailure(error: unknown): ApiClientError {
  return error instanceof ApiClientError ? error : new ApiClientError({ code: 'REQUEST_FAILED', message: 'The request could not be completed. Please retry.' });
}
function Failure({ error, retry }: { error: ApiClientError; retry?: () => void }) {
  return <div className="admin-error" role="alert"><p>{error.message}</p>{retry && <Button onClick={retry}>Retry</Button>}</div>;
}

export function AdminManagement({ module, notify }: { module: Module; notify: (message: string) => void }) {
  const profilesModule = module === 'profiles';
  const singular = profilesModule ? 'User Profile' : 'User Account';
  const [query, setQuery] = useState('');
  const [records, setRecords] = useState<RecordView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [revision, setRevision] = useState(0);
  const [dialog, setDialog] = useState<DialogState | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    setLoading(true); setError(null);
    const timer = setTimeout(() => {
      const operation = profilesModule ? member1Api.profiles(query, abort.signal) : member1Api.accounts(abort.signal);
      operation.then(rows => { if (!abort.signal.aborted) setRecords(rows); })
        .catch(failure => { if (!abort.signal.aborted) setError(asFailure(failure)); })
        .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    }, query ? 200 : 0);
    return () => { abort.abort(); clearTimeout(timer); };
  }, [profilesModule, query, revision]);

  return <>
    <PageHead eyebrow="User Management" title={profilesModule ? 'User Profiles' : 'User Accounts'}
      description={profilesModule ? 'Define the roles available on the platform and the permissions each one grants.' : 'Individual sign-in accounts. Each account is assigned an existing user profile.'}/>
    <div className="search-row">
      {profilesModule && <SearchBox value={query} onChange={setQuery} placeholder="Search profiles by name..."/>}
      <Button kind="primary" onClick={() => setDialog({ action: 'Create' })}><Plus size={18}/>Create {singular}</Button>
    </div>
    {loading ? <p role="status">Loading {profilesModule ? 'profiles' : 'accounts'}…</p>
      : error ? <Failure error={error} retry={() => setRevision(value => value + 1)}/>
      : !records.length ? <Empty title={query ? 'No matching profiles' : `No ${module} yet`} message={query ? 'Try a different profile name.' : `Create a ${singular.toLowerCase()} to get started.`}/>
      : <Table heads={profilesModule ? ['Profile ID', 'Profile Name', 'Role', 'Permissions', 'Status', 'Actions'] : ['Account ID', 'Username', 'Email', 'Assigned Profile', 'Status', 'Actions']}>
        {records.map(record => {
          const profile = 'profileId' in record && 'permissions' in record ? record : null;
          const account = 'accountId' in record ? record : null;
          const id = profile?.profileId ?? account!.accountId;
          return <tr key={id}>
            <td className="mono admin-record-id">{id}</td>
            {profile ? <><td className="strong">{profile.name}</td><td>{roleLabels[profile.role]}</td><td>{profile.permissions.map(permission => permissionLabels[permission]).join(', ')}</td></>
              : <><td className="strong">{account!.username}</td><td>{account!.email}</td><td>{account!.profileName}{account!.profileStatus === 'Suspended' && ' (Suspended)'}</td></>}
            <td><Badge>{record.status}</Badge></td>
            <td><div className="row-actions"><button onClick={() => setDialog({ action: 'View', recordId: id })}>View</button>
              <button onClick={() => setDialog({ action: 'Update', recordId: id })}>Edit</button>
              {profile && profile.status === 'Active' && <button className="danger-link" onClick={() => setDialog({ action: 'Suspend', recordId: id })}>Suspend</button>}
            </div></td>
          </tr>;
        })}
      </Table>}
    <Note>{profilesModule ? 'Changes are saved to the server. Suspending a profile preserves its accounts and blocks protected access.' : 'Accounts are stored on the server. Account search, suspension and shared login/logout are owned by Member 2.'}</Note>
    {dialog && <AdminRecordDialog key={`${module}-${dialog.action}-${dialog.recordId ?? 'new'}`} module={module} state={dialog}
      close={() => setDialog(null)} saved={message => { setDialog(null); notify(message); setRevision(value => value + 1); }}/ >}
  </>;
}

function InputField({ name, label, error, children }: { name: string; label: string; error?: string; children: ReactNode }) {
  return <div className="field"><label htmlFor={`admin-${name}`}>{label} <b aria-hidden="true">*</b></label>{children}
    {error && <small className="admin-field-error" id={`admin-${name}-error`}>{error}</small>}</div>;
}

function AdminRecordDialog({ module, state, close, saved }: {
  module: Module; state: DialogState; close: () => void; saved: (message: string) => void;
}) {
  const profilesModule = module === 'profiles';
  const singular = profilesModule ? 'User Profile' : 'User Account';
  const [record, setRecord] = useState<RecordView | null>(null);
  const [profileOptions, setProfileOptions] = useState<ProfileView[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<ApiClientError | null>(null);
  const [saveError, setSaveError] = useState<ApiClientError | null>(null);
  const [retry, setRetry] = useState(0);
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  const [profileForm, setProfileForm] = useState<ProfileInput>({ name: '', role: 'customer', permissions: [] });
  const [accountForm, setAccountForm] = useState({ username: '', email: '', password: '', profileId: '' });

  useEffect(() => {
    const abort = new AbortController();
    setLoading(true); setLoadError(null);
    async function load(): Promise<void> {
      try {
        const existing = state.recordId ? await (profilesModule ? member1Api.profile(state.recordId, abort.signal) : member1Api.account(state.recordId, abort.signal)) : null;
        const options = !profilesModule && state.action !== 'View' ? await member1Api.profiles('', abort.signal) : [];
        if (abort.signal.aborted) return;
        setRecord(existing); setProfileOptions(options);
        if (existing && 'permissions' in existing) setProfileForm({ name: existing.name, role: existing.role, permissions: [...existing.permissions] });
        if (existing && 'accountId' in existing) setAccountForm({ username: existing.username, email: existing.email, profileId: existing.profileId, password: '' });
      } catch (failure) { if (!abort.signal.aborted) setLoadError(asFailure(failure)); }
      finally { if (!abort.signal.aborted) setLoading(false); }
    }
    void load();
    return () => abort.abort();
  }, [profilesModule, state.recordId, state.action, retry]);

  const fields = saveError?.detail.fields ?? {};
  const controlProps = (name: string) => ({ id: `admin-${name}`, required: true, 'aria-invalid': Boolean(fields[name]), 'aria-describedby': fields[name] ? `admin-${name}-error` : undefined });
  const changeProfile = <K extends keyof ProfileInput,>(key: K, value: ProfileInput[K]): void => setProfileForm(current => ({ ...current, [key]: value }));
  async function submit(): Promise<void> {
    if (inFlight.current) return;
    inFlight.current = true; setSaving(true); setSaveError(null);
    try {
      if (state.action === 'Suspend') await member1Api.suspendProfile(state.recordId!);
      else if (profilesModule) {
        if (state.action === 'Create') await member1Api.createProfile(profileForm);
        else await member1Api.updateProfile(state.recordId!, profileForm);
      } else {
        if (state.action === 'Create') await member1Api.createAccount(accountForm);
        else {
          const { username, email, profileId } = accountForm;
          await member1Api.updateAccount(state.recordId!, { username, email, profileId });
        }
      }
      saved(`${singular} ${state.action === 'Create' ? 'created' : state.action === 'Suspend' ? 'suspended' : 'updated'} successfully.`);
    } catch (failure) { setSaveError(asFailure(failure)); }
    finally { inFlight.current = false; setSaving(false); }
  }

  let rows: [string, ReactNode][] = [];
  if (record && 'permissions' in record) rows = [
    ['Profile ID', record.profileId], ['Profile Name', record.name], ['Role', roleLabels[record.role]],
    ['Permissions', record.permissions.map(permission => permissionLabels[permission]).join(', ')], ['Status', <Badge>{record.status}</Badge>],
  ];
  if (record && 'accountId' in record) rows = [
    ['Account ID', record.accountId], ['Username', record.username], ['Email', record.email],
    ['Assigned Profile', `${record.profileName} (${record.profileId})`], ['Profile Status', record.profileStatus], ['Status', <Badge>{record.status}</Badge>],
  ];
  return <Modal title={`${state.action} ${singular}${state.action === 'Suspend' ? '?' : ''}`} busy={saving} onClose={close}>
    {loading ? <p role="status">Loading {singular.toLowerCase()}…</p>
      : loadError ? <Failure error={loadError} retry={() => setRetry(value => value + 1)}/>
      : state.action === 'View' ? <><Details rows={rows}/><div className="form-actions"><Button onClick={close}>Close</Button></div></>
      : state.action === 'Suspend' ? <>
        <div className="warning-icon"><AlertTriangle/></div><Details rows={rows}/>
        <p className="inline-note">Accounts assigned to this profile cannot access protected functions while their own account status remains unchanged. The profile and all account assignments are preserved. Existing sessions are not revoked by this operation; protected requests must re-check access.</p>
        {saveError && <Failure error={saveError}/>}
        <div className="form-actions"><Button disabled={saving} onClick={close}>Cancel</Button><Button disabled={saving} kind="danger" onClick={() => void submit()}>{saving ? 'Suspending…' : 'Suspend User Profile'}</Button></div>
      </> : <form className="form-stack" onSubmit={event => { event.preventDefault(); void submit(); }}>
        {saveError && <Failure error={saveError}/>}
        <fieldset className="admin-form-fields" disabled={saving}>
          {profilesModule ? <>
            <InputField name="name" label="Profile Name" error={fields.name}><input {...controlProps('name')} value={profileForm.name} maxLength={80} onChange={event => changeProfile('name', event.target.value)} placeholder="e.g. Interior Designer"/></InputField>
            <InputField name="role" label="Role" error={fields.role}><select {...controlProps('role')} value={profileForm.role} onChange={event => changeProfile('role', event.target.value as ProfileInput['role'])}>{ROLE_VALUES.map(role => <option key={role} value={role}>{roleLabels[role]}</option>)}</select></InputField>
            <fieldset className="admin-permissions" aria-required="true" aria-describedby={fields.permissions ? 'admin-permissions-error' : undefined} aria-invalid={Boolean(fields.permissions)}><legend>Permissions <b aria-hidden="true">*</b></legend>
              {PERMISSION_VALUES.map(permission => <label key={permission}><input type="checkbox" checked={profileForm.permissions.includes(permission)} onChange={event => changeProfile('permissions', event.target.checked ? [...profileForm.permissions, permission] : profileForm.permissions.filter(value => value !== permission))}/>{permissionLabels[permission]}</label>)}
              {fields.permissions && <small id="admin-permissions-error" className="admin-field-error">{fields.permissions}</small>}
            </fieldset>
          </> : <>
            <InputField name="username" label="Username" error={fields.username}><input {...controlProps('username')} autoComplete="off" value={accountForm.username} maxLength={40} onChange={event => setAccountForm(current => ({ ...current, username: event.target.value }))} placeholder="e.g. designer02"/></InputField>
            <InputField name="email" label="Email" error={fields.email}><input {...controlProps('email')} type="email" autoComplete="off" value={accountForm.email} maxLength={254} onChange={event => setAccountForm(current => ({ ...current, email: event.target.value }))} placeholder="name@example.com"/></InputField>
            {state.action === 'Create' && <InputField name="password" label="Initial Password" error={fields.password}><input {...controlProps('password')} type="password" autoComplete="new-password" minLength={12} value={accountForm.password} onChange={event => setAccountForm(current => ({ ...current, password: event.target.value }))}/><small>At least 12 characters, at most 72 UTF-8 bytes.</small></InputField>}
            <InputField name="profileId" label="Assigned User Profile" error={fields.profileId}><select {...controlProps('profileId')} value={accountForm.profileId} onChange={event => setAccountForm(current => ({ ...current, profileId: event.target.value }))}>
              <option value="">Select an active profile</option>{profileOptions.filter(profile => profile.status === 'Active' || (record && 'accountId' in record && record.profileId === profile.profileId)).map(profile => <option key={profile.profileId} value={profile.profileId} disabled={profile.status !== 'Active'}>{profile.name}{profile.status === 'Suspended' ? ' (Suspended — current assignment only)' : ''}</option>)}
            </select></InputField>
            {record && 'accountId' in record && record.profileStatus === 'Suspended' && <p className="inline-note">You may retain the existing suspended profile while editing username/email. Access remains blocked until a separate authorized workflow changes it, or you select an active profile.</p>}
          </>}
        </fieldset>
        <div className="form-actions"><Button disabled={saving} onClick={close}>Cancel</Button><Button kind="primary" type="submit" disabled={saving}>{saving ? 'Saving…' : state.action === 'Create' ? `Create ${singular}` : 'Save Changes'}</Button></div>
      </form>}
  </Modal>;
}
