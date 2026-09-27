import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { cancelJob, getJob, getJobs } from '../../api/client';
import { deleteDraft, getDraft, getDrafts, getTextStoryArtifacts, retryTextStory, startTextStory } from '../../api/workflows';
import type { ContentDraft } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { CopyButton } from '../../components/ui/CopyButton';
import { InlineStatus } from '../../components/ui/InlineStatus';
import { ProgressTimeline, type ProgressTimelineStep } from '../../components/ui/ProgressTimeline';
import { Textarea } from '../../components/ui/Textarea';
import { DraftEditor } from '../../features/workflows/DraftEditor';
import { DraftHistory } from '../../features/workflows/DraftHistory';
import { PipelineSelect } from '../../features/workflows/PipelineSelect';

const steps: ProgressTimelineStep[] = [
  { id: 'rewrite', label: 'Short rewrite' }, { id: 'title', label: 'Title' },
  { id: 'image_prompt', label: 'Image prompt' }, { id: 'enhance', label: 'Complete story' },
];

export default function TextStory() {
  const queryClient = useQueryClient();
  const [pipelineId, setPipelineId] = useState('');
  const [sourceText, setSourceText] = useState('');
  const [draftId, setDraftId] = useState('');
  const [jobId, setJobId] = useState('');
  const [error, setError] = useState('');
  const drafts = useQuery({ queryKey: ['drafts', 'text_story'], queryFn: async () => {
    const data = (await getDrafts({ kind: 'text_story', page: 1, page_size: 50 })).data;
    return Array.isArray(data) ? data : data.items;
  } });
  const relatedJobs = useQuery({ queryKey: ['jobs', 'text_story'], queryFn: async () =>
    (await getJobs({ workflow_type: 'text_story', page: 1, page_size: 100 })).data.items });
  const draft = useQuery({ queryKey: ['draft', draftId], queryFn: async () => (await getDraft(draftId)).data,
    enabled: Boolean(draftId), refetchInterval: query => query.state.data?.state === 'generating' ? 1200 : false });
  const artifacts = useQuery({ queryKey: ['text-story-artifacts', draftId], queryFn: async () => (await getTextStoryArtifacts(draftId)).data,
    enabled: Boolean(draftId), refetchInterval: () => draft.data?.state === 'generating' ? 1200 : false });
  const job = useQuery({ queryKey: ['job', jobId], queryFn: async () => (await getJob(jobId)).data,
    enabled: Boolean(jobId), refetchInterval: query => ['queued', 'running'].includes(query.state.data?.status ?? '') ? 1200 : false });

  useEffect(() => { if (artifacts.data?.source_text) setSourceText(artifacts.data.source_text); }, [artifacts.data?.source_text]);
  const onCreated = (data: { draft_id: string; job_id: string }) => {
    setDraftId(data.draft_id); setJobId(data.job_id); setError(''); drafts.refetch(); relatedJobs.refetch();
  };
  const run = useMutation({ mutationFn: () => startTextStory(pipelineId, sourceText), onSuccess: ({ data }) => onCreated(data),
    onError: (reason: any) => { setError(reason.response?.data?.detail || 'Could not start story creation.'); drafts.refetch(); } });
  const retry = useMutation({ mutationFn: () => retryTextStory(draftId), onSuccess: ({ data }) => { onCreated(data); draft.refetch(); artifacts.refetch(); },
    onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not retry story creation.') });
  const cancel = useMutation({ mutationFn: () => cancelJob(jobId), onSuccess: async () => { setError(''); await Promise.all([job.refetch(), draft.refetch(), artifacts.refetch()]); },
    onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not cancel story creation.') });
  const remove = async (item: ContentDraft) => {
    if (!window.confirm('Delete this local draft?')) return;
    await deleteDraft(item.id);
    if (draftId === item.id) { setDraftId(''); setJobId(''); setSourceText(''); }
    drafts.refetch();
  };
  const open = (item: ContentDraft) => {
    setDraftId(item.id); setPipelineId(item.pipeline_id || '');
    setJobId(relatedJobs.data?.find(job => job.draft_id === item.id)?.id || ''); setError('');
  };
  const ready = draft.data && ['ready_for_review', 'publish_failed', 'publishing', 'wordpress_created', 'publish_unknown'].includes(draft.data.state);

  return <div className="space-y-6">
    <header><p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Story composition</p><h1 className="mt-2 text-2xl font-bold text-content-primary">Text Story</h1><p className="mt-1 text-sm text-content-secondary">Paste a story, review its opening and complete ending, then prepare a WordPress draft.</p></header>
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(280px,0.75fr)_minmax(0,1.6fr)]">
      <div className="space-y-5 lg:sticky lg:top-0">
        <Card><CardHeader><CardTitle>Source story</CardTitle></CardHeader><CardContent className="space-y-4">
          <PipelineSelect requiresAI requiresWP value={pipelineId} onChange={setPipelineId} />
          <label className="block text-sm font-medium text-content-primary">Source story<Textarea className="mt-1 min-h-[280px] leading-6" value={sourceText} onChange={event => setSourceText(event.target.value)} placeholder="Paste the original story here..." /></label>
          {error && <InlineStatus tone="error">{error}</InlineStatus>}
          <Button className="w-full" disabled={!pipelineId || !sourceText.trim() || run.isPending} onClick={() => run.mutate()}>{run.isPending ? 'Starting…' : 'Create story'}</Button>
          {draft.data?.state === 'generation_failed' && <Button className="w-full" variant="outline" disabled={retry.isPending} onClick={() => retry.mutate()}>{retry.isPending ? 'Retrying…' : 'Retry failed stage'}</Button>}
        </CardContent></Card>
        {job.data && <Card><CardHeader><div className="flex items-center justify-between gap-3"><CardTitle>Progress</CardTitle>{['queued', 'running'].includes(job.data.status) && <Button variant="outline" size="sm" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Cancel</Button>}</div></CardHeader><CardContent className="space-y-3"><ProgressTimeline progress={job.data.progress} current={job.data.current_step} status={job.data.status} detail={job.data.logs?.at(-1)?.detail} startedAt={job.data.start_time} updatedAt={job.data.updated_at || job.data.logs?.at(-1)?.timestamp} failedStep={job.data.outputs?.failed_step} cancelledStep={job.data.outputs?.cancelled_step} steps={steps} logs={job.data.logs} />{job.data.outputs?.capacity_unverified && <InlineStatus tone="warning">AI context capacity is unverified. Review the full result before publishing.</InlineStatus>}</CardContent></Card>}
      </div>
      <div className="space-y-5">
        <Card><CardHeader><div className="flex items-center justify-between"><CardTitle>Short rewrite</CardTitle><CopyButton value={artifacts.data?.rewrite_text || ''} /></div></CardHeader><CardContent><div className="whitespace-pre-wrap text-sm leading-7 text-content-primary">{artifacts.data?.rewrite_text || 'The 550–650 word opening appears here after the first step.'}</div></CardContent></Card>
        <Card><CardHeader><div className="flex items-center justify-between"><CardTitle>Image prompt</CardTitle><CopyButton value={artifacts.data?.image_prompt || ''} /></div></CardHeader><CardContent><div className="whitespace-pre-wrap text-sm leading-7 text-content-primary">{artifacts.data?.image_prompt || 'A copyable image prompt appears here after the third step.'}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Review & publish</CardTitle></CardHeader><CardContent>{ready && draft.data ? <DraftEditor draft={draft.data} onUpdated={item => queryClient.setQueryData(['draft', item.id], item)} /> : <div className="py-16 text-center text-sm text-content-tertiary">{draft.data?.title && <p className="mb-3 font-semibold text-content-primary">{draft.data.title}</p>}{draft.data?.error || 'The full story editor becomes available when all four steps finish.'}</div>}</CardContent></Card>
      </div>
    </div>
    <section><h2 className="mb-3 text-lg font-bold">Text story history</h2><DraftHistory drafts={drafts.data ?? []} activeId={draftId} onOpen={open} onDelete={remove} /></section>
  </div>;
}
