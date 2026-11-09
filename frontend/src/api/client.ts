import axios from 'axios';
import { Account, Pipeline, Job, JobPage, AccountConfig, Language, AppSettings, AIModel } from './types';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin),
});

export const getAccounts = () => client.get<Account[]>('/accounts');
export const createAccount = (data: Partial<Account>) => client.post<Account>('/accounts', data);
export const updateAccount = (id: string, data: Partial<Account>) => client.put<Account>(`/accounts/${id}`, data);
export const deleteAccount = (id: string) => client.delete(`/accounts/${id}`);
export const testAccount = (data: { id?: string; type?: string; config?: AccountConfig }) => client.post('/accounts/test', data);
export const getWPCategories = (config: AccountConfig) => client.post('/accounts/wp-categories', config);
export const getAIModels = (config: Pick<AccountConfig, 'base_url' | 'api_key'>) =>
  client.post<AIModel[]>('/accounts/ai-models', config);
export interface BenchmarkSample { id: string; source_language: string; target_language: string; word_count: number; text: string }
export const getBenchmarkSample = () => client.get<BenchmarkSample>('/model-benchmarks/sample');
export const getBenchmarkModels = (accountId: string) => client.get<AIModel[]>(`/model-benchmarks/accounts/${accountId}/models`);
export const startBenchmark = (accountId: string, modelIds: string[]) =>
  client.post<{ job_id: string; status: string }>('/model-benchmarks', { account_id: accountId, model_ids: modelIds });

export const getPipelines = (includeWorkflows = false) => client.get<Pipeline[]>('/pipelines', { params: { include_workflows: includeWorkflows } });
export const createPipeline = (data: Partial<Pipeline>) => client.post<Pipeline>('/pipelines', data);
export const updatePipeline = (id: string, data: Partial<Pipeline>) => client.put<Pipeline>(`/pipelines/${id}`, data);
export const deletePipeline = (id: string) => client.delete(`/pipelines/${id}`);
export const runPipeline = (id: string, data: any) => client.post<{ job_id: string }>(`/pipelines/${id}/run`, data);

export const getLanguages = () => client.get<Language[]>('/languages');
export const createLanguage = (data: Omit<Language, 'created_at'>) =>
  client.post<Language>('/languages', data);
export const updateLanguage = (
  code: string,
  data: Pick<Language, 'display_name' | 'is_active'>,
) => client.put<Language>(`/languages/${code}`, data);

export const getSettings = () => client.get<AppSettings>('/settings');
export const updateSettings = (data: AppSettings) =>
  client.put<AppSettings>('/settings', data);
export const checkProxy = (proxyUrls: string[]) =>
  client.post<{ ok: boolean; proxy_index: number; checked: number }>('/settings/proxy/check', { proxy_urls: proxyUrls });
export const getDatabaseInfo = () => client.get<{
  size_bytes: number | null;
  database: string;
  articles: number;
  enrichments: number;
  jobs: number;
  drafts: number;
}>('/settings/database-info');

export const getJobs = (params?: { page?: number; page_size?: number; workflow_type?: string; status_group?: 'active' | 'history'; status?: 'success' | 'failed' | 'cancelled' }) =>
  client.get<JobPage>('/jobs', { params });
export const getJob = (id: string) => client.get<Job>(`/jobs/${id}`);
export const syncJob = (id: string) => client.post(`/jobs/${id}/sync`);
export const cancelJob = (id: string) => client.post<{ status: string }>(`/jobs/${id}/cancel`);

export default client;
