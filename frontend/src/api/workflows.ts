import client from './client';
import type { ContentDraft, TextStoryArtifacts } from './types';
import { normalizeSourceUrl } from '../utils/sourceUrl';

export const getDrafts = (params?: { kind?: string; pipeline_id?: string; page?: number; page_size?: number }) =>
  client.get<ContentDraft[] | { items: ContentDraft[]; total: number; page: number; page_size: number }>('/content-drafts', { params });
export const getPipelineCategories = (id: string) =>
  client.get<Array<{ id: string | number; name: string; count: number }>>(`/pipelines/${id}/wp-categories`);
export const getDraft = (id: string) => client.get<ContentDraft>(`/content-drafts/${id}`);
export const getDraftCategories = (id: string) =>
  client.get<Array<{ id: string | number; name: string; count: number }>>(`/content-drafts/${id}/wp-categories`);
export const createDraft = (data: Partial<ContentDraft>) => client.post<ContentDraft>('/content-drafts', data);
export const updateDraft = (id: string, data: Partial<ContentDraft> & { version: number }) =>
  client.put<ContentDraft>(`/content-drafts/${id}`, { ...data, ...(data.source_url ? { source_url: normalizeSourceUrl(data.source_url) } : {}) });
export const deleteDraft = (id: string) => client.delete(`/content-drafts/${id}`);
export const uploadDraftImage = (id: string, image: File) => {
  const form = new FormData();
  form.append('image', image);
  return client.post<ContentDraft>(`/content-drafts/${id}/image`, form);
};
export const publishDraft = (id: string, confirmed: boolean) =>
  client.post<ContentDraft>(`/content-drafts/${id}/publish`, { confirmed });

export const startRewrite = (pipelineId: string, sourceUrl: string, useProxy = false, rerunFromJobId?: string, useEnrichment = false) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/rewrite-jobs', { pipeline_id: pipelineId, source_url: normalizeSourceUrl(sourceUrl), use_proxy: useProxy, use_enrichment: useEnrichment, ...(rerunFromJobId ? { rerun_from_job_id: rerunFromJobId } : {}) });
export const startArticleWorkflow = (pipelineId: string, sourceUrl: string, mode: 'v1' | 'v2' = 'v2', useProxy = false, rerunFromJobId?: string, useEnrichment = false) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/article-workflows/run', { pipeline_id: pipelineId, source_url: normalizeSourceUrl(sourceUrl), mode, use_proxy: useProxy, use_enrichment: useEnrichment, ...(rerunFromJobId ? { rerun_from_job_id: rerunFromJobId } : {}) });
export const retryArticleWorkflow = (jobId: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>(`/article-workflows/${jobId}/retry`);
export interface ManualArticleWorkflowInput {
  pipelineId: string;
  mode: 'v1' | 'v2';
  title: string;
  content: string;
  imageUrl?: string;
  image?: File;
}
export const startManualArticleWorkflow = (input: ManualArticleWorkflowInput) => {
  const form = new FormData();
  form.append('pipeline_id', input.pipelineId);
  form.append('mode', input.mode);
  form.append('title', input.title);
  form.append('content', input.content);
  if (input.imageUrl) form.append('image_url', input.imageUrl);
  if (input.image) form.append('image', input.image);
  return client.post<{ job_id: string; draft_id: string; status: string }>('/article-workflows/run-text', form);
};
export const startGeneration = (pipelineId: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/generation-jobs', { pipeline_id: pipelineId });
export const startTextStory = (pipeline_id: string, source_text: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>('/text-story-jobs', { pipeline_id, source_text });
export const getTextStoryArtifacts = (draftId: string) =>
  client.get<TextStoryArtifacts>(`/text-story-jobs/${draftId}/artifacts`);
export const retryTextStory = (draftId: string) =>
  client.post<{ job_id: string; draft_id: string; status: string }>(`/text-story-jobs/${draftId}/retry`);

export const resolveDelivery = (jobId: string, data: { channel: string; outcome: string; external_id?: string; url?: string; confirmed: boolean }) =>
  client.post(`/article-workflows/${jobId}/resolve-delivery`, data);
