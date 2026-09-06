import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Sparkles } from 'lucide-react';
import { getJob } from '../../api/client';
import { deleteDraft, getDraft, getDrafts, startGeneration } from '../../api/workflows';
import type { ContentDraft } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { InlineStatus } from '../../components/ui/InlineStatus';
import { ProgressTimeline } from '../../components/ui/ProgressTimeline';
import { DraftEditor } from '../../features/workflows/DraftEditor';
import { DraftHistory } from '../../features/workflows/DraftHistory';
import { ProfileManager } from '../../features/workflows/ProfileManager';

export default function GenerateStory() {
  const queryClient = useQueryClient();
  const [profileId, setProfileId] = useState('');
  const [draftId, setDraftId] = useState('');
  const [jobId, setJobId] = useState('');
  const [error, setError] = useState('');
  const drafts = useQuery({ queryKey: ['drafts', 'generated'], queryFn: async () => (await getDrafts({ kind: 'generated' })).data });
  const draft = useQuery({ queryKey: ['draft', draftId], queryFn: async () => (await getDraft(draftId)).data, enabled: Boolean(draftId), refetchInterval: query => query.state.data?.state === 'generating' ? 1200 : false });
  const job = useQuery({ queryKey: ['job', jobId], queryFn: async () => (await getJob(jobId)).data, enabled: Boolean(jobId), refetchInterval: query => ['queued', 'running'].includes(query.state.data?.status ?? '') ? 1200 : false });
  const run = useMutation({ mutationFn: () => startGeneration(profileId), onSuccess: ({ data }) => { setDraftId(data.draft_id); setJobId(data.job_id); setError(''); drafts.refetch(); }, onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not start generation.') });
  const remove = async (item: ContentDraft) => { if (window.confirm('Delete this local draft?')) { await deleteDraft(item.id); if (draftId === item.id) setDraftId(''); drafts.refetch(); } };
  return <div className="space-y-6">
    <header><p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Pattern-guided agent</p><h1 className="mt-2 text-2xl font-bold text-content-primary">Generate Story</h1><p className="mt-1 text-sm text-content-secondary">The agent chooses stored themes and structures. You always review before WordPress.</p></header>
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(280px,0.75fr)_minmax(0,1.6fr)]"><div className="space-y-5 lg:sticky lg:top-0"><Card><CardHeader><CardTitle>Setup</CardTitle></CardHeader><CardContent className="space-y-4"><ProfileManager type="generate_story" value={profileId} onChange={setProfileId} />{error && <InlineStatus tone="error">{error}</InlineStatus>}<Button className="w-full" disabled={!profileId || run.isPending} onClick={() => run.mutate()}><Sparkles size={16} className="mr-2" />{run.isPending ? 'Starting…' : 'Generate new story'}</Button></CardContent></Card>{job.data && <Card><CardHeader><CardTitle>Agent progress</CardTitle></CardHeader><CardContent><ProgressTimeline progress={job.data.progress} current={job.data.current_step} />{job.data.status === 'failed' && <div className="mt-4"><InlineStatus tone="error">{job.data.logs?.at(-1)?.detail || 'Generation failed.'}</InlineStatus></div>}</CardContent></Card>}</div><Card><CardHeader><CardTitle>Review & publish</CardTitle></CardHeader><CardContent>{draft.data ? <DraftEditor draft={draft.data} onUpdated={item => queryClient.setQueryData(['draft', item.id], item)} /> : <div className="py-24 text-center text-content-tertiary">Generate or open a saved draft.</div>}</CardContent></Card></div>
    <section><h2 className="mb-3 text-lg font-bold">Generated story history</h2><DraftHistory drafts={drafts.data ?? []} activeId={draftId} onOpen={item => setDraftId(item.id)} onDelete={remove} /></section>
  </div>;
}
