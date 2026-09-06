import type { ContentDraft } from '../../api/types';
import { Clock3, Trash2 } from 'lucide-react';
import { Button } from '../../components/ui/Button';

export function DraftHistory({ drafts, activeId, onOpen, onDelete }: { drafts: ContentDraft[]; activeId?: string; onOpen: (draft: ContentDraft) => void; onDelete: (draft: ContentDraft) => void }) {
  if (!drafts.length) return <p className="rounded-xl border border-dashed border-border-default p-6 text-center text-sm text-content-tertiary">No saved drafts yet.</p>;
  return <div className="space-y-2">
    {drafts.map(draft => <div key={draft.id} className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${draft.id === activeId ? 'border-accent bg-accent/5' : 'border-border-default bg-surface hover:bg-surface-subtle'}`}>
      <button type="button" onClick={() => onOpen(draft)} className="min-w-0 flex-1 cursor-pointer text-left">
        <p className="truncate text-sm font-semibold text-content-primary">{draft.title || 'Untitled draft'}</p>
        <p className="mt-1 flex items-center gap-1 text-xs text-content-tertiary"><Clock3 size={12} />{new Date(draft.updated_at).toLocaleString()} · {draft.state.replaceAll('_', ' ')}</p>
      </button>
      {!['publishing', 'wordpress_created'].includes(draft.state) && <Button type="button" variant="ghost" size="icon" title="Delete draft" onClick={() => onDelete(draft)}><Trash2 size={15} /></Button>}
    </div>)}
  </div>;
}
