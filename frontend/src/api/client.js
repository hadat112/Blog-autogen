import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

export const getAccounts = () => client.get('/accounts');
export const createAccount = (data) => client.post('/accounts', data);
export const updateAccount = (id, data) => client.put(`/accounts/${id}`, data);
export const deleteAccount = (id) => client.delete(`/accounts/${id}`);
export const testAccount = (id) => client.post(`/accounts/${id}/test`);

export const getPipelines = () => client.get('/pipelines');
export const createPipeline = (data) => client.post('/pipelines', data);
export const updatePipeline = (id, data) => client.put(`/pipelines/${id}`, data);
export const deletePipeline = (id) => client.delete(`/pipelines/${id}`);
export const runPipeline = (id, data) => client.post(`/pipelines/${id}/run`, data);

export const getJobs = () => client.get('/jobs');
export const getJob = (id) => client.get(`/jobs/${id}`);

export default client;
