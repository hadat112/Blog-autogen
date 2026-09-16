import client from './client';
import type { ContentDraft } from './types';

export const getDrafts = (params?: { kind?: string; pipeline_id?: string; page?: number; page_size?: number }) =>
  client.get<ContentDraft[] | { items: ContentDraft[]; total: number; page: number; page_size: number }>('/content-drafts', { params });
export const getPipelineCategories = (id: string) =>
  client.get<Array<{ id: string | number; name: string; count: number }>>(`/pipelines/${id}/wp-categories`);
export const getDraft = (id: string) => client.get<ContentDraft>(`/content-drafts/${id}`);
export const getDraftCategories = (id: string) =>
  client.get<Array<{ id: string | number; name: string; count: number }>>(`/content-drafts/${id}/wp-categories`);
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

export const startRewrite = (pipelineId: string, sourceUrl: string, rerunFromJobId?: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/rewrite-jobs', { pipeline_id: pipelineId, source_url: sourceUrl, ...(rerunFromJobId ? { rerun_from_job_id: rerunFromJobId } : {}) });
export const startArticleWorkflow = (pipelineId: string, sourceUrl: string, mode: 'v1' | 'v2' = 'v2', rerunFromJobId?: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/article-workflows/run', { pipeline_id: pipelineId, source_url: sourceUrl, mode, ...(rerunFromJobId ? { rerun_from_job_id: rerunFromJobId } : {}) });
export const retryArticleWorkflow = (jobId: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>(`/article-workflows/${jobId}/retry`);
export const startGeneration = (pipelineId: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/generation-jobs', { pipeline_id: pipelineId });
