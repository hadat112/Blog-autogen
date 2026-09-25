import client from './client';
import type { PatternArticle, ThemeRule } from './types';

export const getPatternSummary = () => client.get<{ total: number; completed: number; recoverable: number; distinct_themes: number }>('/patterns/summary');
export const getPatterns = (params: Record<string, string | number | undefined>) =>
  client.get<{ items: PatternArticle[]; total: number; page: number; page_size: number }>('/patterns', { params });
export const getPattern = (id: string) => client.get<PatternArticle>(`/patterns/${id}`);
export const deletePattern = (id: string) => client.delete(`/patterns/${id}`);
export const retryPattern = (id: string, pipelineId: string) =>
  client.post(`/patterns/${id}/retry-analysis`, null, { params: { pipeline_id: pipelineId } });

export const getThemeRules = () => client.get<ThemeRule[]>('/theme-rules');
export const createThemeRule = (data: Omit<ThemeRule, 'id' | 'created_at' | 'updated_at'>) => client.post<ThemeRule>('/theme-rules', data);
export const updateThemeRule = (id: string, data: Omit<ThemeRule, 'id' | 'created_at' | 'updated_at'>) => client.put<ThemeRule>(`/theme-rules/${id}`, data);
export const deleteThemeRule = (id: string) => client.delete(`/theme-rules/${id}`);

export interface PatternAnalysisPipeline { pipeline_id: string; name: string; type: string; can_analyze: boolean }
export const getPatternAnalysisPipelines = () => client.get<PatternAnalysisPipeline[]>('/pattern-analysis-pipelines');
export interface ArticleEnrichment {
  article_id: string;
  summary: string | null;
  plot_beats: unknown;
  characters: unknown;
  setting: unknown;
  conflict: unknown;
  emotional_arc: unknown;
  creative_dna: unknown;
  summary_status: 'missing' | 'queued' | 'processing' | 'completed' | 'failed';
  analysis_status: 'missing' | 'queued' | 'processing' | 'completed' | 'failed';
  dna_status: 'missing' | 'queued' | 'processing' | 'completed' | 'failed';
  summary_error?: string | null;
  analysis_error?: string | null;
  dna_error?: string | null;
  ai_account_id?: string | null;
  model: string;
  updated_at: string;
}
export const getPatternEnrichment = (id: string) => client.get<ArticleEnrichment>(`/patterns/${id}/enrichment`);
export const enqueuePatternEnrichment = (id: string, step: 'summary' | 'analysis' | 'dna') =>
  client.post<{ job_id: string | null; status: string }>(`/patterns/${id}/enrichment/${step}`);
export const enqueueMissingEnrichment = () =>
  client.post<{ queued: number }>('/patterns/enrichment/bulk');
