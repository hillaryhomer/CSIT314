import { api } from '../member2';
import type { AccountInput, AccountView, ApiErrorBody, CreateAccountInput, ProfileInput, ProfileView } from './types';

export class ApiClientError extends Error {
  constructor(public readonly detail: ApiErrorBody['error']) { super(detail.message); }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  try { return await api<T>(path, options.method ?? 'GET', options.body ? JSON.parse(String(options.body)) : undefined, options.signal ?? undefined); }
  catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    const failure = error as Error & { fields?: Record<string, string>; code?: ApiErrorBody['error']['code'] };
    throw new ApiClientError({ code: failure.code ?? 'REQUEST_FAILED', message: failure.message, fields: failure.fields ?? {} });
  }
}

export const member1Api = {
  profiles: (name = '', signal?: AbortSignal): Promise<ProfileView[]> => request(`/profiles?name=${encodeURIComponent(name)}`, { signal }),
  profile: (profileId: string, signal?: AbortSignal): Promise<ProfileView> => request(`/profiles/${encodeURIComponent(profileId)}`, { signal }),
  createProfile: (input: ProfileInput): Promise<ProfileView> => request('/profiles', { method: 'POST', body: JSON.stringify(input) }),
  updateProfile: (profileId: string, input: ProfileInput): Promise<ProfileView> => request(`/profiles/${encodeURIComponent(profileId)}`, { method: 'PUT', body: JSON.stringify(input) }),
  suspendProfile: (profileId: string): Promise<ProfileView> => request(`/profiles/${encodeURIComponent(profileId)}/suspend`, { method: 'POST', body: '{}' }),
  accounts: (signal?: AbortSignal, query = ''): Promise<AccountView[]> => request(`/accounts?q=${encodeURIComponent(query)}`, { signal }),
  suspendAccount: (id: string): Promise<AccountView> => request(`/accounts/${encodeURIComponent(id)}/suspend`, { method: 'POST', body: '{}' }),
  account: (accountId: string, signal?: AbortSignal): Promise<AccountView> => request(`/accounts/${encodeURIComponent(accountId)}`, { signal }),
  createAccount: (input: CreateAccountInput): Promise<AccountView> => request('/accounts', { method: 'POST', body: JSON.stringify(input) }),
  updateAccount: (accountId: string, input: AccountInput): Promise<AccountView> => request(`/accounts/${encodeURIComponent(accountId)}`, { method: 'PUT', body: JSON.stringify(input) }),
};
