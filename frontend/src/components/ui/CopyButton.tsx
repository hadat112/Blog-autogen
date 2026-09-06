import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Button } from './Button';

export function CopyButton({ value, label = 'Copy' }: { value: string; label?: string }) {
  const [status, setStatus] = useState('');
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setStatus('Copied');
    } catch {
      window.prompt('Copy this value manually:', value);
      setStatus('Select and copy manually');
    }
    window.setTimeout(() => setStatus(''), 1800);
  };
  return (
    <div className="inline-flex items-center gap-2">
      <Button type="button" variant="outline" size="sm" onClick={copy} disabled={!value}>
        {status === 'Copied' ? <Check size={14} className="mr-1.5" /> : <Copy size={14} className="mr-1.5" />}{label}
      </Button>
      <span className="sr-only" aria-live="polite">{status}</span>
    </div>
  );
}
