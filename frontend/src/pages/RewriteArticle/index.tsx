import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, WandSparkles, XCircle } from 'lucide-react';
import { cancelJob, getJob } from '../../api/client';
import { deleteDraft, getDraft, getDrafts, startRewrite } from '../../api/workflows';
import type { ContentDraft } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { InlineStatus } from '../../components/ui/InlineStatus';
import { Input } from '../../components/ui/Input';
import { ProgressTimeline } from '../../components/ui/ProgressTimeline';
import { DraftEditor } from '../../features/workflows/DraftEditor';
import { DraftHistory } from '../../features/workflows/DraftHistory';
import { ProfileManager } from '../../features/workflows/ProfileManager';

export default function RewriteArticle() {
  const queryClient = useQueryClient();
  const [profileId, setProfileId] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [draftId, setDraftId] = useState('');
  const [jobId, setJobId] = useState('');
  const [error, setError] = useState('');
  const drafts = useQuery({ queryKey: ['drafts', 'rewrite'], queryFn: async () => (await getDrafts({ kind: 'rewrite' })).data });
  const draft = useQuery({ queryKey: ['draft', draftId], queryFn: async () => (await getDraft(draftId)).data, enabled: Boolean(draftId), refetchInterval: query => ['generating', 'publishing'].includes(query.state.data?.state ?? '') ? 1200 : false });
  const job = useQuery({ queryKey: ['job', jobId], queryFn: async () => (await getJob(jobId)).data, enabled: Boolean(jobId), refetchInterval: query => ['queued', 'running'].includes(query.state.data?.status ?? '') ? 1200 : false });
  const run = useMutation({
    mutationFn: () => startRewrite(profileId, sourceUrl),
    onSuccess: ({ data }) => { setDraftId(data.draft_id); setJobId(data.job_id); setError(''); queryClient.invalidateQueries({ queryKey: ['drafts'] }); },
    onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not start rewrite.'),
  });
  const cancel = useMutation({
    mutationFn: () => cancelJob(jobId),
    onSuccess: async () => { setError(''); await Promise.all([job.refetch(), draft.refetch(), drafts.refetch()]); },
    onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not cancel rewrite.'),
  });
  const remove = async (item: ContentDraft) => { if (window.confirm('Delete this local draft?')) { await deleteDraft(item.id); if (draftId === item.id) setDraftId(''); drafts.refetch(); } };
  return <div className="space-y-6">
    <header><p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Content workflow</p><h1 className="mt-2 text-2xl font-bold text-content-primary">Rewrite Article</h1><p className="mt-1 text-sm text-content-secondary">Transform a WordPress reference into a new localized story, review it, then publish.</p></header>
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(280px,0.75fr)_minmax(0,1.6fr)]">
      <div className="space-y-5 lg:sticky lg:top-0">
        <Card><CardHeader><CardTitle>Setup</CardTitle></CardHeader><CardContent className="space-y-4"><ProfileManager type="rewrite" value={profileId} onChange={setProfileId} /><label className="block text-sm font-medium">WordPress source URL<Input className="mt-1" type="url" value={sourceUrl} onChange={event => setSourceUrl(event.target.value)} placeholder="https://site.example/story" /></label>{error && <InlineStatus tone="error">{error}</InlineStatus>}<Button className="w-full" disabled={!profileId || !sourceUrl || run.isPending} onClick={() => run.mutate()}><WandSparkles size={16} className="mr-2" />{run.isPending ? 'Starting…' : 'Start rewrite'}</Button></CardContent></Card>
        {(job.data || run.isPending) && <Card><CardHeader><div className="flex items-center justify-between gap-3"><CardTitle>Progress</CardTitle>{job.data && ['queued', 'running'].includes(job.data.status) && <Button variant="outline" size="sm" className="text-status-danger" disabled={cancel.isPending} onClick={() => cancel.mutate()}><XCircle size={14} className="mr-1.5" />{cancel.isPending ? 'Cancelling…' : 'Cancel'}</Button>}</div></CardHeader><CardContent><ProgressTimeline progress={job.data?.progress ?? 0} current={job.data?.current_step} />{job.data?.status === 'cancelled' && <div className="mt-4"><InlineStatus tone="warning">Rewrite cancelled. The draft was preserved for recovery.</InlineStatus></div>}{job.data?.status === 'failed' && <div className="mt-4"><InlineStatus tone="error">{job.data.logs?.at(-1)?.detail || 'Rewrite failed. Your draft was preserved.'}</InlineStatus></div>}</CardContent></Card>}
      </div>
      <Card><CardHeader><div className="flex items-center justify-between"><CardTitle>Review & publish</CardTitle>{draftId && <Button variant="ghost" size="icon" title="Refresh draft" onClick={() => draft.refetch()}><RefreshCw size={16} /></Button>}</div></CardHeader><CardContent>{draft.data ? <DraftEditor draft={draft.data} onUpdated={item => queryClient.setQueryData(['draft', item.id], item)} /> : <div className="py-24 text-center text-content-tertiary">Start a rewrite or open a saved draft.</div>}</CardContent></Card>
    </div>
    <section><h2 className="mb-3 text-lg font-bold text-content-primary">Rewrite history</h2><DraftHistory drafts={drafts.data ?? []} activeId={draftId} onOpen={item => setDraftId(item.id)} onDelete={remove} /></section>
  </div>;
}
