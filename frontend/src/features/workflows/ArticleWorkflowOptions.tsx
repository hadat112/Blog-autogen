import { useEffect, useId, useState } from 'react';
import type { Pipeline } from '../../api/types';
import { Select } from '../../components/ui/Select';

export function useArticleWorkflowVersion() {
  const [mode, setMode] = useState<'v1' | 'v2'>(() =>
    window.localStorage.getItem('story-autogen-workflow-version') === 'v2' ? 'v2' : 'v1');
  useEffect(() => { window.localStorage.setItem('story-autogen-workflow-version', mode); }, [mode]);
  return [mode, setMode] as const;
}

export function ArticleWorkflowVersion({ mode, onChange, disabled = false }: {
  mode: 'v1' | 'v2'; onChange: (mode: 'v1' | 'v2') => void; disabled?: boolean;
}) {
  return <div className="flex h-7 rounded-md border border-border-default bg-surface-subtle p-0.5" role="group" aria-label="Version">
    {(['v1', 'v2'] as const).map(option => <button key={option} type="button"
      aria-pressed={mode === option} disabled={disabled} onClick={() => onChange(option)}
      className={`min-w-10 rounded px-2 text-[10px] font-bold transition-colors ${mode === option ? 'bg-surface text-accent shadow-sm' : 'text-content-tertiary hover:text-content-primary'}`}>
      {option.toUpperCase()}
    </button>)}
  </div>;
}

export function ArticleWorkflowPipeline({ pipelines, value, onChange, disabled = false }: {
  pipelines: Pipeline[]; value: string; onChange: (value: string) => void; disabled?: boolean;
}) {
  const id = useId();
  return <div className="w-full space-y-1.5">
    <label htmlFor={id} className="ml-0.5 text-[10px] font-bold uppercase tracking-widest text-content-tertiary">Select Pipeline</label>
    <Select id={id} value={value} disabled={disabled} onChange={event => onChange(event.target.value)}
      className="bg-surface-subtle focus:bg-surface transition-colors border-border-default">
      {pipelines.map(p => <option key={p.id} value={p.id}>{p.name} ({p.language})</option>)}
      {pipelines.length === 0 && <option value="">No AI + WP pipeline found</option>}
    </Select>
  </div>;
}
