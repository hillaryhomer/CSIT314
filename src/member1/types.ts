export const ROLE_VALUES = ['admin', 'designer', 'customer', 'manager'] as const;
export type ProfileRole = typeof ROLE_VALUES[number];
export const PERMISSION_VALUES = [
  'profiles:read', 'profiles:write', 'accounts:read', 'accounts:write',
  'projects:manage', 'projects:discover', 'reports:read', 'categories:manage',
] as const;
export type Permission = typeof PERMISSION_VALUES[number];
export type RecordStatus = 'Active' | 'Suspended';

export interface ProfileView {
  profileId: string;
  name: string;
  role: ProfileRole;
  permissions: Permission[];
  status: RecordStatus;
}
export interface ProfileInput {
  name: string;
  role: ProfileRole;
  permissions: Permission[];
}
export interface AccountView {
  accountId: string;
  username: string;
  email: string;
  profileId: string;
  profileName: string;
  profileStatus: RecordStatus;
  status: RecordStatus;
}
export interface AccountInput {
  username: string;
  email: string;
  profileId: string;
}
export interface CreateAccountInput extends AccountInput { password: string }
export type ErrorCode = 'VALIDATION' | 'DUPLICATE' | 'NOT_FOUND' | 'FORBIDDEN' |
  'UNAUTHENTICATED' | 'ALREADY_SUSPENDED' | 'PERSISTENCE' | 'REQUEST_FAILED';
export interface ApiErrorBody {
  error: { code: ErrorCode; message: string; fields?: Record<string, string> };
}
