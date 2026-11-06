export type ProjectStatus = 'Current' | 'Past';
export type ProjectImage = { imageId: string; url: string };
export type ProjectRecord = {
  projectId: string; ownerAccountId: string; companyId: string | null;
  title: string; description: string; categoryId: string; categoryName: string;
  categoryStatus: 'Active' | 'Suspended'; style: string; status: ProjectStatus;
  createdAt: string; updatedAt: string; images: ProjectImage[];
  companyName: string | null; designerName: string;
};
export type Category = { categoryId: string; name: string; description: string; status: 'Active' | 'Suspended' };
export type DraftImage = { imageId?: string; url: string; data?: string; mimeType?: string };
export type ProjectInput = { title: string; description: string; categoryId: string; style: string };
export const collection = (status: ProjectStatus) => `/designer/projects/${status.toLowerCase()}`;
export const placeholderImage = '/images/interior-1.jpg';
