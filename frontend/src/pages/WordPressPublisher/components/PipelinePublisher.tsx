import { useEffect, useId, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ImagePlus, Send, X } from 'lucide-react';
import { cancelJob, getJob, getPipelines } from '../../../api/client';
import { retryArticleWorkflow, startManualArticleWorkflow } from '../../../api/workflows';
import { Button } from '../../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card';
import { InlineStatus } from '../../../components/ui/InlineStatus';
import { Input } from '../../../components/ui/Input';
import { Textarea } from '../../../components/ui/Textarea';
import { ArticleWorkflowPipeline, ArticleWorkflowVersion, useArticleWorkflowVersion } from '../../../features/workflows/ArticleWorkflowOptions';
import JobCard from '../../Dashboard/components/JobCard';
import JobDetailsModal from '../../Dashboard/components/JobDetailsModal';

const savedJobKey = 'story-autogen-publisher-pipeline-job';

export function PipelinePublisher() {
  const queryClient = useQueryClient();
  const contentId = useId();
  const [pipelineId, setPipelineId] = useState('');
  const [mode, setMode] = useArticleWorkflowVersion();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [image, setImage] = useState<File>();
  const fileRef = useRef<HTMLInputElement>(null);
  const [jobId, setJobId] = useState(() => window.localStorage.getItem(savedJobKey) || '');
  const [showDetails, setShowDetails] = useState(false);
  const [error, setError] = useState('');
  const pipelines = useQuery({ queryKey: ['pipelines'], queryFn: async () => (await getPipelines(true)).data });
  const available = (pipelines.data ?? []).filter(p => p.is_active && p.step_accounts?.ai && p.step_accounts?.wp);
  useEffect(() => {
    if (!available.some(p => p.id === pipelineId)) setPipelineId(available[0]?.id ?? '');
  }, [pipelines.data, pipelineId]);
  const job = useQuery({
    queryKey: ['jobs', jobId], queryFn: async () => (await getJob(jobId)).data,
    enabled: Boolean(jobId), retry: false,
    refetchInterval: query => ['queued', 'running'].includes(query.state.data?.status ?? '') ? 3000 : false,
  });
  const selectJob = (id: string) => {
    setJobId(id);
    window.localStorage.setItem(savedJobKey, id);
    setError('');
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
  };
  const reportError = (reason: any) => setError(reason.response?.data?.detail || reason.message || 'Workflow failed.');
  const run = useMutation({
    mutationFn: () => startManualArticleWorkflow({ pipelineId, mode, title, content,
      imageUrl: imageUrl.trim() || undefined, image }),
    onSuccess: ({ data }) => selectJob(data.job_id), onError: reportError,
  });
  const retry = useMutation({ mutationFn: () => retryArticleWorkflow(jobId),
    onSuccess: ({ data }) => selectJob(data.job_id), onError: reportError });
  const cancel = useMutation({ mutationFn: () => cancelJob(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }), onError: reportError });
  const removeImage = () => {
    setImage(undefined); setImageUrl('');
    if (fileRef.current) fileRef.current.value = '';
  };

  return <div className="space-y-6">
    <Card>
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
        <CardTitle>Run workflow</CardTitle>
        <ArticleWorkflowVersion mode={mode} onChange={setMode} disabled={run.isPending} />
      </CardHeader>
      <CardContent>
        <form className="space-y-5" onSubmit={event => { event.preventDefault(); if (pipelineId && title.trim() && content.trim()) run.mutate(); }}>
          <ArticleWorkflowPipeline pipelines={available} value={pipelineId} onChange={setPipelineId} disabled={run.isPending} />
          {pipelines.isError && <InlineStatus tone="error">Could not load pipelines. Reload the page to try again.</InlineStatus>}
          <p className="text-sm text-content-secondary">Runs the Dashboard workflow and publishes automatically to the pipeline’s configured channels.</p>
          <label className="block text-sm font-medium">Source title
            <Input className="mt-1" required value={title} onChange={e => setTitle(e.target.value)} disabled={run.isPending} />
          </label>
          <div className="text-sm font-medium"><label htmlFor={contentId}>Source content</label>
            <Textarea id={contentId} className="mt-1 min-h-[320px] leading-6" required value={content} onChange={e => setContent(e.target.value)} disabled={run.isPending} />
          </div>
          <p className="text-xs text-content-tertiary">{content.length.toLocaleString()} characters · Split automatically using the selected AI account’s character limit.</p>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
            <label className="block min-w-0 text-sm font-medium">Source image URL
              <Input className="mt-1" type="url" placeholder="Optional" value={imageUrl} onChange={e => setImageUrl(e.target.value)} disabled={Boolean(image) || run.isPending} />
            </label>
            <label className={`mt-6 inline-flex h-9 cursor-pointer items-center justify-center rounded-md border border-border-default px-4 text-sm font-medium ${imageUrl || run.isPending ? 'pointer-events-none opacity-50' : 'hover:bg-surface-subtle'}`}>
              <ImagePlus size={15} className="mr-2" />Upload image
              <input ref={fileRef} className="sr-only" type="file" aria-label="Source image upload"
                accept="image/jpeg,image/png,image/webp,image/gif" disabled={Boolean(imageUrl) || run.isPending}
                onChange={e => setImage(e.target.files?.[0])} />
            </label>
          </div>
          {(image || imageUrl) && <div className="flex min-w-0 items-center justify-between gap-2 rounded-md border border-border-default p-3 text-xs">
            <span className="min-w-0 truncate">{image?.name || imageUrl}</span>
            <Button type="button" variant="ghost" size="sm" disabled={run.isPending} onClick={removeImage} aria-label="Remove source image"><X size={14} /></Button>
          </div>}
          {error && <InlineStatus tone="error">{error}</InlineStatus>}
          <div className="flex justify-end"><Button type="submit" disabled={run.isPending || !pipelineId || !title.trim() || !content.trim()}>
            <Send size={15} className="mr-2" />{run.isPending ? 'Starting…' : 'Run workflow'}
          </Button></div>
        </form>
      </CardContent>
    </Card>
    {job.isError && <InlineStatus tone="error">Could not load the saved job. Open Dashboard to check its status.</InlineStatus>}
    {job.data && <section className="space-y-3"><h2 className="text-lg font-bold">Latest workflow</h2>
      <JobCard job={job.data} onClick={() => setShowDetails(true)} onRerun={() => retry.mutate()}
        isRerunning={retry.isPending} onCancel={() => cancel.mutate()} isCancelling={cancel.isPending} />
    </section>}
    {showDetails && job.data && <JobDetailsModal job={job.data} onClose={() => setShowDetails(false)} />}
  </div>;
}
