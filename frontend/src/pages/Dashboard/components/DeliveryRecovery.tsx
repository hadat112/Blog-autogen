import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resolveDelivery } from '../../../api/workflows';

export function DeliveryRecovery({ jobId, channels }: { jobId: string; channels: string[] }) {
  const [outcome, setOutcome] = useState('not_sent');
  const [externalId, setExternalId] = useState('');
  const [url, setUrl] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const cache = useQueryClient();
  const channel = channels[0];
  const resolution = useMutation({
    mutationFn: () => resolveDelivery(jobId, { channel, outcome, external_id: externalId, url, confirmed }),
    onSuccess: () => { setConfirmed(false); cache.invalidateQueries({ queryKey: ['jobs'] }); },
  });
  return <div className="mt-3 space-y-2 rounded-md border border-amber-300 p-3 text-xs" onClick={event => event.stopPropagation()}>
    <p className="font-semibold">Verify {channel} before resuming</p>
    <p>The last request may have succeeded. Check the destination first to avoid duplicate posts.</p>
    <select aria-label="Verified delivery outcome" className="w-full rounded border p-2" value={outcome} onChange={event => setOutcome(event.target.value)}>
      <option value="not_sent">Verified: not delivered — allow retry</option>
      <option value="sent">Verified: already delivered — keep result</option>
    </select>
    {outcome === 'sent' && channel !== 'telegram' && <input aria-label="Existing post ID" className="w-full rounded border p-2" placeholder="Existing post ID" value={externalId} onChange={event => setExternalId(event.target.value)} />}
    {outcome === 'sent' && channel === 'wordpress' && <input aria-label="Existing post URL" className="w-full rounded border p-2" placeholder="https://…" value={url} onChange={event => setUrl(event.target.value)} />}
    <label className="flex items-center gap-2"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />I checked the destination and confirm this result.</label>
    <button className="rounded border px-3 py-2 disabled:opacity-50" disabled={!confirmed || resolution.isPending} onClick={() => resolution.mutate()}>{resolution.isPending ? 'Saving…' : 'Save verified result'}</button>
    {resolution.isError && <p role="alert">{(resolution.error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Could not save verification. Try again.'}</p>}
  </div>;
}
