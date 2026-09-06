import client from './client';
import type { ContentDraft, WorkflowProfile, WorkflowType } from './types';

export type WorkflowProfilePayload = Omit<WorkflowProfile, 'id' | 'created_at'>;

export const getWorkflowProfiles = (type: WorkflowType) =>
  client.get<WorkflowProfile[]>('/workflow-profiles', { params: { type } });
export const createWorkflowProfile = (data: WorkflowProfilePayload) =>
  client.post<WorkflowProfile>('/workflow-profiles', data);
export const updateWorkflowProfile = (id: string, data: WorkflowProfilePayload) =>
  client.put<WorkflowProfile>(`/workflow-profiles/${id}`, data);
export const deleteWorkflowProfile = (id: string) => client.delete(`/workflow-profiles/${id}`);
export const getWorkflowCategories = (id: string) =>
  client.get<Array<{ id: string | number; name: string; count: number }>>(`/workflow-profiles/${id}/wp-categories`);

export const getDrafts = (params?: { kind?: string; pipeline_id?: string }) =>
  client.get<ContentDraft[]>('/content-drafts', { params });
export const getDraft = (id: string) => client.get<ContentDraft>(`/content-drafts/${id}`);
export const createDraft = (data: Partial<ContentDraft>) => client.post<ContentDraft>('/content-drafts', data);
export const updateDraft = (id: string, data: Partial<ContentDraft> & { version: number }) =>
  client.put<ContentDraft>(`/content-drafts/${id}`, data);
export const deleteDraft = (id: string) => client.delete(`/content-drafts/${id}`);
export const uploadDraftImage = (id: string, image: File) => {
  const form = new FormData();
  form.append('image', image);
  return client.post<ContentDraft>(`/content-drafts/${id}/image`, form);
};
export const publishDraft = (id: string, confirmed: boolean) =>
  client.post<ContentDraft>(`/content-drafts/${id}/publish`, { confirmed });

export const startRewrite = (profileId: string, sourceUrl: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/rewrite-jobs', { profile_id: profileId, source_url: sourceUrl });
export const startGeneration = (profileId: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/generation-jobs', { profile_id: profileId });
