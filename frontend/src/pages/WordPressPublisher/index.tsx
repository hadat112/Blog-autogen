import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FilePlus2 } from 'lucide-react';
import { createDraft, deleteDraft, getDrafts } from '../../api/workflows';
import type { ContentDraft } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { InlineStatus } from '../../components/ui/InlineStatus';
import { DraftEditor } from '../../features/workflows/DraftEditor';
import { DraftHistory } from '../../features/workflows/DraftHistory';
import { ProfileManager } from '../../features/workflows/ProfileManager';

export default function WordPressPublisher() {
  const queryClient = useQueryClient();
  const [profileId, setProfileId] = useState('');
  const [active, setActive] = useState<ContentDraft | null>(null);
  const [error, setError] = useState('');
  const drafts = useQuery({ queryKey: ['drafts', 'manual'], queryFn: async () => (await getDrafts({ kind: 'manual' })).data });
  const create = useMutation({ mutationFn: () => createDraft({ kind: 'manual', pipeline_id: profileId, title: '', content: '', content_format: 'plain', wp_status: 'draft' }), onSuccess: ({ data }) => { setActive(data); setError(''); drafts.refetch(); }, onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not create draft.') });
  const remove = async (item: ContentDraft) => { if (window.confirm('Delete this local draft and its pending upload?')) { await deleteDraft(item.id); if (active?.id === item.id) setActive(null); drafts.refetch(); } };
  return <div className="space-y-6">
    <header><p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Focused publishing</p><h1 className="mt-2 text-2xl font-bold">WordPress Publisher</h1><p className="mt-1 text-sm text-content-secondary">Write, preview, and publish to WordPress from one place. No Facebook actions.</p></header>
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(280px,0.75fr)_minmax(0,1.6fr)]"><Card className="lg:sticky lg:top-0"><CardHeader><CardTitle>Destination</CardTitle></CardHeader><CardContent className="space-y-4"><ProfileManager type="wp_publish" value={profileId} onChange={setProfileId} />{error && <InlineStatus tone="error">{error}</InlineStatus>}<Button className="w-full" disabled={!profileId || create.isPending} onClick={() => create.mutate()}><FilePlus2 size={16} className="mr-2" />New post draft</Button></CardContent></Card><Card><CardHeader><CardTitle>Compose</CardTitle></CardHeader><CardContent>{active ? <DraftEditor key={active.id} draft={active} manual onUpdated={item => { setActive(item); queryClient.invalidateQueries({ queryKey: ['drafts'] }); }} /> : <div className="py-24 text-center text-content-tertiary">Create a new draft or open one from history.</div>}</CardContent></Card></div>
    <section><h2 className="mb-3 text-lg font-bold">Publisher history</h2><DraftHistory drafts={drafts.data ?? []} activeId={active?.id} onOpen={setActive} onDelete={remove} /></section>
  </div>;
}
