import axios from 'axios';
import { Account, Pipeline, Job, AccountConfig } from './types';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin),
});

export const getAccounts = () => client.get<Account[]>('/accounts');
export const createAccount = (data: Partial<Account>) => client.post<Account>('/accounts', data);
export const updateAccount = (id: string, data: Partial<Account>) => client.put<Account>(`/accounts/${id}`, data);
export const deleteAccount = (id: string) => client.delete(`/accounts/${id}`);
export const testAccount = (data: { id?: string; type?: string; config?: AccountConfig }) => client.post('/accounts/test', data);
export const getWPCategories = (config: AccountConfig) => client.post('/accounts/wp-categories', config);

export const getPipelines = () => client.get<Pipeline[]>('/pipelines');
export const createPipeline = (data: Partial<Pipeline>) => client.post<Pipeline>('/pipelines', data);
export const updatePipeline = (id: string, data: Partial<Pipeline>) => client.put<Pipeline>(`/pipelines/${id}`, data);
export const deletePipeline = (id: string) => client.delete(`/pipelines/${id}`);
export const runPipeline = (id: string, data: any) => client.post<{ job_id: string }>(`/pipelines/${id}/run`, data);

export const getJobs = () => client.get<Job[]>('/jobs');
export const getJob = (id: string) => client.get<Job>(`/jobs/${id}`);
export const syncJob = (id: string) => client.post(`/jobs/${id}/sync`);
export const cancelJob = (id: string) => client.post<{ status: string }>(`/jobs/${id}/cancel`);

export default client;
