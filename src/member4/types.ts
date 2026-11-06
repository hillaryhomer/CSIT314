import type { ProjectRecord } from '../member3/types';

export type CustomerProject = Omit<ProjectRecord, 'ownerAccountId' | 'companyId'> & {
  saved: boolean;
  savedAt?: string;
};
export type SaveResult = { project: CustomerProject; saved: true; created: boolean };
