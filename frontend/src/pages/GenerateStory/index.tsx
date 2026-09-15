import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Sparkles, XCircle } from 'lucide-react';
import { cancelJob, getJob } from '../../api/client';
import { deleteDraft, getDraft, getDrafts, startGeneration } from '../../api/workflows';
import type { ContentDraft } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { InlineStatus } from '../../components/ui/InlineStatus';
import { ProgressTimeline, type ProgressTimelineStep } from '../../components/ui/ProgressTimeline';
import { DraftEditor } from '../../features/workflows/DraftEditor';
import { DraftHistory } from '../../features/workflows/DraftHistory';
import { PipelineSelect } from '../../features/workflows/PipelineSelect';

const generateProgressSteps: ProgressTimelineStep[] = [
  { id: 'choose_patterns', label: 'Choose story patterns' },
  { id: 'agent', label: 'Agent' },
  { id: 'prepare_review', label: 'Prepare review' },
];

export default function GenerateStory() {
  const queryClient = useQueryClient();
  const [pipelineId, setPipelineId] = useState('');
  const [draftId, setDraftId] = useState('');
  const [jobId, setJobId] = useState('');
  const [error, setError] = useState('');
  const drafts = useQuery({ queryKey: ['drafts', 'generated'], queryFn: async () => { const data = (await getDrafts({ kind: 'generated', page: 1, page_size: 50 })).data; return Array.isArray(data) ? data : data.items; } });
  const draft = useQuery({ queryKey: ['draft', draftId], queryFn: async () => (await getDraft(draftId)).data, enabled: Boolean(draftId), refetchInterval: query => query.state.data?.state === 'generating' ? 1200 : false });
  const job = useQuery({ queryKey: ['job', jobId], queryFn: async () => (await getJob(jobId)).data, enabled: Boolean(jobId), refetchInterval: query => ['queued', 'running'].includes(query.state.data?.status ?? '') ? 1200 : false });
  const run = useMutation({ mutationFn: () => startGeneration(pipelineId), onSuccess: ({ data }) => { setDraftId(data.draft_id); setJobId(data.job_id); setError(''); drafts.refetch(); }, onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not start generation.') });
  const cancel = useMutation({ mutationFn: () => cancelJob(jobId), onSuccess: async () => { setError(''); await Promise.all([job.refetch(), draft.refetch(), drafts.refetch()]); }, onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not cancel generation.') });
  const remove = async (item: ContentDraft) => { if (window.confirm('Delete this local draft?')) { await deleteDraft(item.id); if (draftId === item.id) setDraftId(''); drafts.refetch(); } };
  return <div className="space-y-6">
    <header><p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Pattern-guided agent</p><h1 className="mt-2 text-2xl font-bold text-content-primary">Generate Story</h1><p className="mt-1 text-sm text-content-secondary">Select a saved pipeline. The agent uses its configured AI and WordPress accounts.</p></header>
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(280px,0.75fr)_minmax(0,1.6fr)]"><div className="space-y-5 lg:sticky lg:top-0"><Card><CardHeader><CardTitle>Setup</CardTitle></CardHeader><CardContent className="space-y-4"><PipelineSelect requiresAI value={pipelineId} onChange={setPipelineId} />{error && <InlineStatus tone="error">{error}</InlineStatus>}<Button className="w-full" disabled={!pipelineId || run.isPending} onClick={() => run.mutate()}><Sparkles size={16} className="mr-2" />{run.isPending ? 'Starting…' : 'Generate new story'}</Button></CardContent></Card>{job.data && <Card><CardHeader><div className="flex items-center justify-between gap-3"><CardTitle>Agent progress</CardTitle>{['queued', 'running'].includes(job.data.status) && <Button variant="outline" size="sm" className="text-status-danger" disabled={cancel.isPending} onClick={() => cancel.mutate()}><XCircle size={14} className="mr-1.5" />{cancel.isPending ? 'Cancelling…' : 'Cancel'}</Button>}</div></CardHeader><CardContent><ProgressTimeline progress={job.data.progress} current={job.data.current_step} status={job.data.status} detail={job.data.logs?.at(-1)?.detail} startedAt={job.data.start_time} updatedAt={job.data.updated_at || job.data.logs?.at(-1)?.timestamp} failedStep={job.data.outputs?.failed_step} cancelledStep={job.data.outputs?.cancelled_step} steps={generateProgressSteps} logs={job.data.logs} />{job.data.status === 'cancelled' && <div className="mt-4"><InlineStatus tone="warning">Generation cancelled. The draft was preserved for recovery.</InlineStatus></div>}{job.data.status === 'failed' && <div className="mt-4"><InlineStatus tone="error">{job.data.logs?.at(-1)?.detail || 'Generation failed.'}</InlineStatus></div>}</CardContent></Card>}</div><Card><CardHeader><CardTitle>Review & publish</CardTitle></CardHeader><CardContent>{draft.data ? <DraftEditor draft={draft.data} onUpdated={item => queryClient.setQueryData(['draft', item.id], item)} /> : <div className="py-24 text-center text-content-tertiary">Generate or open a saved draft.</div>}</CardContent></Card></div>
    <section><h2 className="mb-3 text-lg font-bold">Generated story history</h2><DraftHistory drafts={drafts.data ?? []} activeId={draftId} onOpen={item => setDraftId(item.id)} onDelete={remove} /></section>
  </div>;
}
