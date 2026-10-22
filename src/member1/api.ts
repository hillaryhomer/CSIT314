import type { AccountInput, AccountView, ApiErrorBody, CreateAccountInput, ProfileInput, ProfileView } from './types';

export class ApiClientError extends Error {
  constructor(public readonly detail: ApiErrorBody['error']) { super(detail.message); }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new ApiClientError({ code: 'REQUEST_FAILED', message: 'Could not reach the server. Check the connection and retry.' });
  }
  let body: unknown;
  try { body = await response.json(); } catch {
    throw new ApiClientError({ code: 'REQUEST_FAILED', message: 'The server returned an unreadable response. Please retry.' });
  }
  if (!response.ok) {
    const failure = body as Partial<ApiErrorBody>;
    throw new ApiClientError(failure?.error ?? { code: 'REQUEST_FAILED', message: 'The request failed. Please retry.' });
  }
  return body as T;
}

export const member1Api = {
  profiles: (name = '', signal?: AbortSignal): Promise<ProfileView[]> => request(`/profiles?name=${encodeURIComponent(name)}`, { signal }),
  profile: (profileId: string, signal?: AbortSignal): Promise<ProfileView> => request(`/profiles/${encodeURIComponent(profileId)}`, { signal }),
  createProfile: (input: ProfileInput): Promise<ProfileView> => request('/profiles', { method: 'POST', body: JSON.stringify(input) }),
  updateProfile: (profileId: string, input: ProfileInput): Promise<ProfileView> => request(`/profiles/${encodeURIComponent(profileId)}`, { method: 'PUT', body: JSON.stringify(input) }),
  suspendProfile: (profileId: string): Promise<ProfileView> => request(`/profiles/${encodeURIComponent(profileId)}/suspend`, { method: 'POST', body: '{}' }),
  accounts: (signal?: AbortSignal): Promise<AccountView[]> => request('/accounts', { signal }),
  account: (accountId: string, signal?: AbortSignal): Promise<AccountView> => request(`/accounts/${encodeURIComponent(accountId)}`, { signal }),
  createAccount: (input: CreateAccountInput): Promise<AccountView> => request('/accounts', { method: 'POST', body: JSON.stringify(input) }),
  updateAccount: (accountId: string, input: AccountInput): Promise<AccountView> => request(`/accounts/${encodeURIComponent(accountId)}`, { method: 'PUT', body: JSON.stringify(input) }),
};
