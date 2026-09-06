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

export interface CollectionSource { pipeline_id: string; name: string; type: string; collect_patterns: boolean; can_analyze: boolean }
export const getCollectionSources = () => client.get<CollectionSource[]>('/pattern-collection-sources');
export const updateCollectionSource = (id: string, collect_patterns: boolean) =>
  client.put(`/pattern-collection-sources/${id}`, { collect_patterns });
