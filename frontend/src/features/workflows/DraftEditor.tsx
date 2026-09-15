import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, ImagePlus, Save, Send, X } from 'lucide-react';
import type { ContentDraft } from '../../api/types';
import { getDraftCategories, getPipelineCategories, publishDraft, updateDraft, uploadDraftImage } from '../../api/workflows';
import { Button } from '../../components/ui/Button';
import { CopyButton } from '../../components/ui/CopyButton';
import { InlineStatus } from '../../components/ui/InlineStatus';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Tabs } from '../../components/ui/Tabs';
import { Textarea } from '../../components/ui/Textarea';
import { plainTextPreview, sanitizePreviewHtml } from './sanitizePreview';

export function DraftEditor({ draft, manual = false, onUpdated }: { draft: ContentDraft; manual?: boolean; onUpdated: (draft: ContentDraft) => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(draft);
  const [tab, setTab] = useState<'write' | 'preview'>('write');
  const [error, setError] = useState('');
  useEffect(() => setForm(draft), [draft]);
  const categories = useQuery({
    queryKey: ['draft-categories', form.id, form.pipeline_id, form.wp_account_id],
    queryFn: async () => (await (form.pipeline_id ? getPipelineCategories(form.pipeline_id) : getDraftCategories(form.id))).data,
    enabled: Boolean(form.pipeline_id || form.wp_account_id), retry: false,
  });
  const editable = !['publishing', 'wordpress_created'].includes(form.state);
  const captionValid = !form.caption || form.content.startsWith(form.caption);
  const preview = useMemo(() => sanitizePreviewHtml(form.content_format === 'html' ? form.content : plainTextPreview(form.content)), [form.content, form.content_format]);

  const save = useMutation({
    mutationFn: () => updateDraft(form.id, {
      pipeline_id: form.pipeline_id, wp_account_id: form.wp_account_id, kind: form.kind, source_url: form.source_url, language: form.language,
      title: form.title, content: form.content, caption: form.caption,
      image_kind: form.image_kind, image_source: form.image_source,
      content_format: form.content_format, category_id: form.category_id,
      wp_status: form.wp_status, version: form.version,
    }),
    onSuccess: ({ data }) => { setError(''); setForm(data); onUpdated(data); queryClient.invalidateQueries({ queryKey: ['drafts'] }); },
    onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not save draft.'),
  });
  const upload = useMutation({
    mutationFn: (file: File) => uploadDraftImage(form.id, file),
    onSuccess: ({ data }) => { setForm(data); onUpdated(data); },
    onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not upload image.'),
  });
  const publish = useMutation({
    mutationFn: async () => {
      if (!form.title.trim() || !form.content.trim()) throw new Error('Title and content are required.');
      await save.mutateAsync();
      const confirmed = form.wp_status === 'publish' ? window.confirm('Publish this post publicly on WordPress now?') : true;
      if (!confirmed) throw new Error('Publication cancelled.');
      return publishDraft(form.id, form.wp_status === 'publish');
    },
    onSuccess: ({ data }) => { setError(''); setForm(data); onUpdated(data); queryClient.invalidateQueries({ queryKey: ['jobs'] }); },
    onError: (reason: any) => setError(reason.response?.data?.detail || reason.message || 'WordPress publication failed.'),
  });

  const update = <K extends keyof ContentDraft>(key: K, value: ContentDraft[K]) => setForm(current => ({ ...current, [key]: value }));

  return <div className="space-y-5">
    {form.error && <InlineStatus tone="error">{form.error}</InlineStatus>}
    {error && <InlineStatus tone="error">{error}</InlineStatus>}
    {form.state === 'wordpress_created' && form.wp_url && <div className="rounded-xl border border-status-success/30 bg-status-success/10 p-4"><p className="mb-3 font-semibold text-status-success">Created in WordPress</p><div className="flex flex-wrap gap-2"><CopyButton value={form.wp_url} label="Copy link" />{!manual && form.caption && <CopyButton value={form.caption} label="Copy caption" />}<a href={form.wp_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center rounded-md px-3 text-sm font-medium text-accent hover:bg-accent/10">Open <ExternalLink size={14} className="ml-1.5" /></a></div></div>}

    <label className="block text-sm font-medium">Title<Input className="mt-1" value={form.title} disabled={!editable} onChange={event => update('title', event.target.value)} /></label>
    {manual && <div className="flex flex-wrap items-center justify-between gap-3"><Tabs value={form.content_format} onChange={value => update('content_format', value)} items={[{ value: 'plain', label: 'Plain text' }, { value: 'html', label: 'HTML' }]} /><Tabs value={tab} onChange={setTab} items={[{ value: 'write', label: 'Write' }, { value: 'preview', label: 'Preview' }]} /></div>}
    {tab === 'write' ? <label className="block text-sm font-medium">Content<Textarea className="mt-1 min-h-[360px] font-mono leading-6" value={form.content} disabled={!editable} onChange={event => update('content', event.target.value)} /></label> : <div className="prose prose-zinc max-w-none rounded-xl border border-border-default bg-surface p-5 text-content-primary" dangerouslySetInnerHTML={{ __html: preview }} />}
    {!manual && <div className="space-y-2"><label className="block text-sm font-medium">Caption<Textarea className="mt-1 min-h-28" value={form.caption ?? ''} disabled={!editable} onChange={event => update('caption', event.target.value)} /></label>{form.caption && <InlineStatus tone={captionValid ? 'success' : 'warning'}>{captionValid ? 'Caption matched' : 'Caption differs from story opening'}</InlineStatus>}</div>}
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="block text-sm font-medium">Category<Select className="mt-1" value={form.category_id ?? ''} disabled={!editable} onChange={event => update('category_id', event.target.value || null)}><option value="">Uncategorized</option>{(categories.data ?? []).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
      <label className="block text-sm font-medium">WordPress status<Select className="mt-1" value={form.wp_status} disabled={!editable} onChange={event => update('wp_status', event.target.value as 'draft' | 'publish')}><option value="draft">Create WordPress draft</option><option value="publish">Publish now</option></Select></label>
    </div>
    <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
      <label className="block text-sm font-medium">Featured image URL <span className="text-content-tertiary">(optional)</span><Input className="mt-1" type="url" value={form.image_kind === 'url' ? form.image_source ?? '' : ''} disabled={!editable || form.image_kind === 'upload'} onChange={event => { update('image_kind', event.target.value ? 'url' : null); update('image_source', event.target.value || null); }} /></label>
      <label className={`mt-6 inline-flex h-9 cursor-pointer items-center justify-center rounded-md border border-border-default bg-surface px-4 text-sm font-medium hover:bg-surface-subtle ${!editable || form.image_kind === 'url' ? 'pointer-events-none opacity-50' : ''}`}><ImagePlus size={15} className="mr-2" />{upload.isPending ? 'Uploading…' : form.image_kind === 'upload' ? 'Replace upload' : 'Upload image'}<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/gif" disabled={!editable || form.image_kind === 'url'} onChange={event => { const file = event.target.files?.[0]; if (file) upload.mutate(file); }} /></label>
    </div>
    {form.image_source && <div className="flex items-center justify-between rounded-lg border border-border-default bg-surface-subtle px-3 py-2 text-xs text-content-secondary"><span className="min-w-0 truncate">Featured image: {form.image_kind === 'upload' ? 'local upload' : form.image_source}</span><Button type="button" variant="ghost" size="sm" disabled={!editable} onClick={() => setForm(current => ({ ...current, image_kind: null, image_source: null }))}><X size={13} className="mr-1" />Remove</Button></div>}
    <div className="sticky bottom-0 flex flex-wrap justify-end gap-2 border-t border-border-default bg-surface/95 py-3 backdrop-blur"><Button type="button" variant="outline" onClick={() => save.mutate()} disabled={!editable || save.isPending}><Save size={15} className="mr-2" />Save</Button><Button type="button" onClick={() => publish.mutate()} disabled={!editable || publish.isPending}><Send size={15} className="mr-2" />{publish.isPending ? 'Sending…' : form.wp_status === 'publish' ? 'Publish now' : 'Create WP draft'}</Button></div>
  </div>;
}
