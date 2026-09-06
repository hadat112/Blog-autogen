import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export function InlineStatus({ tone = 'info', children }: { tone?: 'info' | 'success' | 'error'; children: React.ReactNode }) {
  const Icon = tone === 'success' ? CheckCircle2 : tone === 'error' ? AlertCircle : Loader2;
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} aria-live="polite" className={`flex items-start gap-2 rounded-lg border p-3 text-sm ${tone === 'error' ? 'border-status-danger/30 bg-status-danger/10 text-status-danger' : tone === 'success' ? 'border-status-success/30 bg-status-success/10 text-status-success' : 'border-border-default bg-surface-subtle text-content-secondary'}`}>
      <Icon size={16} className={tone === 'info' ? 'mt-0.5 animate-spin' : 'mt-0.5'} />
      <span>{children}</span>
    </div>
  );
}
