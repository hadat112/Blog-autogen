import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import { Clock3, Loader2, RefreshCw } from 'lucide-react';
import { cancelJob, getAccounts, getBenchmarkModels, getBenchmarkSample, getJob, getJobs, startBenchmark } from '../api/client';
import type { AIModel, Job } from '../api/types';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Select } from '../components/ui/Select';

type ResultRow = { model_id: string; status: 'waiting' | 'running' | 'success' | 'error' | 'cancelled'; elapsed_seconds: number | null; error?: string };

function errorMessage(error: unknown): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') return error.response.data.detail;
  return 'Request failed. Check the AI account and try again.';
}

function rowsFrom(job?: Job): ResultRow[] {
  const rows = job?.outputs?.results;
  return Array.isArray(rows) ? rows as ResultRow[] : [];
}

const tone: Record<ResultRow['status'], string> = {
  waiting: 'text-content-tertiary', running: 'text-accent', success: 'text-status-success',
  error: 'text-status-danger', cancelled: 'text-content-tertiary',
};

export default function ModelBenchmark() {
  const [accountId, setAccountId] = useState('');
  const [models, setModels] = useState<AIModel[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [jobId, setJobId] = useState('');
  const [message, setMessage] = useState('');
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: async () => (await getAccounts()).data.filter(account => account.type === 'ai') });
  const sample = useQuery({ queryKey: ['model-benchmark-sample'], queryFn: async () => (await getBenchmarkSample()).data });
  const history = useQuery({ queryKey: ['model-benchmark-history'], queryFn: async () => (await getJobs({ workflow_type: 'model_benchmark', page_size: 20 })).data.items,
    refetchInterval: query => query.state.data?.some(job => ['queued', 'running'].includes(job.status)) ? 1500 : false });
  const activeId = jobId || history.data?.[0]?.id || '';
  const job = useQuery({ queryKey: ['job', activeId], queryFn: async () => (await getJob(activeId)).data, enabled: Boolean(activeId),
    refetchInterval: query => ['queued', 'running'].includes(query.state.data?.status ?? '') ? 1000 : false });
  const fetchModels = useMutation({ mutationFn: async () => (await getBenchmarkModels(accountId)).data,
    onSuccess: data => { setModels(data); setSelected([]); setMessage(data.length ? '' : 'This account returned no models.'); },
    onError: error => setMessage(errorMessage(error)) });
  const run = useMutation({ mutationFn: async () => (await startBenchmark(accountId, selected)).data,
    onSuccess: data => { setJobId(data.job_id); setMessage(''); history.refetch(); },
    onError: error => setMessage(errorMessage(error)) });
  const cancel = useMutation({ mutationFn: () => cancelJob(activeId), onSuccess: () => { job.refetch(); history.refetch(); },
    onError: error => setMessage(errorMessage(error)) });
  const active = ['queued', 'running'].includes(job.data?.status ?? '');
  const toggle = (modelId: string) => setSelected(current => current.includes(modelId) ? current.filter(id => id !== modelId) : current.length < 5 ? [...current, modelId] : current);

  return <div className="space-y-6">
    <header>
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">AI tools / timing</p>
      <h1 className="mt-2 text-2xl font-bold text-content-primary">Model Benchmark</h1>
      <p className="mt-1 text-sm text-content-secondary">Translate the same fixed story into Polish with up to five models, one after another.</p>
    </header>
    <Card><CardHeader><CardTitle>Set up a run</CardTitle></CardHeader><CardContent className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <label className="space-y-1 text-sm font-medium text-content-primary">AI account
          <Select value={accountId} onChange={event => { setAccountId(event.target.value); setModels([]); setSelected([]); setMessage(''); }}>
            <option value="">Select an AI account</option>
            {accounts.data?.map(account => <option key={account.id} value={account.id}>{account.name}</option>)}
          </Select>
        </label>
        <Button variant="outline" disabled={!accountId || fetchModels.isPending} onClick={() => fetchModels.mutate()}>
          {fetchModels.isPending ? <Loader2 size={15} className="mr-2 animate-spin" /> : <RefreshCw size={15} className="mr-2" />}Fetch models
        </Button>
      </div>
      {accounts.data?.length === 0 && <p className="text-sm text-content-secondary">Add an AI account in Accounts to start a benchmark.</p>}
      {models.length > 0 && <div>
        <div className="mb-2 flex items-center justify-between text-sm"><span className="font-medium text-content-primary">Choose models</span><span className="text-content-tertiary">{selected.length}/5 selected · minimum 2</span></div>
        <div className="grid max-h-64 gap-2 overflow-y-auto sm:grid-cols-2 lg:grid-cols-3">
          {models.map(model => <label key={model.id} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition-colors ${selected.includes(model.id) ? 'border-accent bg-accent/5' : 'border-border-default hover:bg-surface-subtle'}`}>
            <input type="checkbox" className="accent-[var(--button-primary-bg)]" checked={selected.includes(model.id)} disabled={!selected.includes(model.id) && selected.length >= 5} onChange={() => toggle(model.id)} />
            <span className="min-w-0"><span className="block truncate font-medium text-content-primary">{model.name || model.id}</span>{model.name && model.name !== model.id && <span className="block truncate text-xs text-content-tertiary">{model.id}</span>}</span>
          </label>)}
        </div>
        {selected.length > 0 && <p className="mt-2 text-xs text-content-tertiary">Run order: {selected.join(' → ')}</p>}
      </div>}
      <details className="rounded-lg border border-border-default p-4"><summary className="cursor-pointer text-sm font-medium text-content-primary">Fixed sample · English → Polish{sample.data && ` · ${sample.data.word_count} words`}</summary>
        <pre className="mt-3 max-h-60 overflow-y-auto whitespace-pre-wrap font-sans text-xs leading-5 text-content-secondary">{sample.data?.text || 'Loading sample…'}</pre>
      </details>
      {message && <p role="alert" className="text-sm text-status-danger">{message}</p>}
      <Button disabled={!accountId || selected.length < 2 || run.isPending || active} onClick={() => run.mutate()}>{run.isPending ? 'Starting…' : 'Run benchmark'}</Button>
    </CardContent></Card>
    <Card><CardHeader><div className="flex items-center justify-between gap-3"><CardTitle>Results</CardTitle>{active && <Button variant="outline" size="sm" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Cancel run</Button>}</div></CardHeader><CardContent>
      {job.data ? <div className="space-y-4"><div className="flex flex-wrap items-center gap-3 text-sm text-content-secondary"><Clock3 size={16} /><span className="capitalize">{job.data.status.replace('_', ' ')}</span><span>·</span><span>{new Date(job.data.start_time).toLocaleString()}</span></div>
        <div className="overflow-x-auto rounded-lg border border-border-default"><table className="w-full text-left text-sm"><thead className="bg-surface-subtle text-xs uppercase tracking-wide text-content-tertiary"><tr><th className="px-4 py-3">Model</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Time</th></tr></thead><tbody className="divide-y divide-border-default">
          {rowsFrom(job.data).map((row, index) => <tr key={`${row.model_id}-${index}`}><td className="px-4 py-3 font-medium text-content-primary">{row.model_id}</td><td className={`px-4 py-3 font-medium capitalize ${tone[row.status]}`}>{row.status}{row.error && <span className="ml-2 font-normal text-content-secondary">· {row.error}</span>}</td><td className="px-4 py-3 text-right tabular-nums text-content-primary">{row.elapsed_seconds == null ? '—' : `${row.elapsed_seconds.toFixed(2)} s`}</td></tr>)}
        </tbody></table></div></div> : <p className="py-12 text-center text-sm text-content-tertiary">Run a benchmark to compare response times.</p>}
    </CardContent></Card>
    {(history.data?.length ?? 0) > 0 && <section><h2 className="mb-3 text-lg font-bold text-content-primary">Recent runs</h2><div className="space-y-2">{history.data?.map(item => <button key={item.id} onClick={() => setJobId(item.id)} className={`flex w-full items-center justify-between rounded-lg border px-4 py-3 text-left text-sm hover:bg-surface-subtle ${activeId === item.id ? 'border-accent bg-accent/5' : 'border-border-default bg-surface'}`}><span className="text-content-primary">{new Date(item.start_time).toLocaleString()} · {(item.outputs?.model_ids as string[] | undefined)?.length ?? 0} models</span><span className="capitalize text-content-secondary">{item.status.replace('_', ' ')}</span></button>)}</div></section>}
  </div>;
}
