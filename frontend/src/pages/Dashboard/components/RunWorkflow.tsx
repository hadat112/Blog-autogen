import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useArticleWorkflowVersion } from '../../../features/workflows/ArticleWorkflowOptions';
import QuickRun from './QuickRun';
import { ManualArticleRun } from './ManualArticleRun';

type InputMode = 'v1' | 'v2' | 'v3';
const inputModeKey = 'story-autogen-dashboard-input-mode';

export function RunWorkflow({ onRunStarted }: { onRunStarted: (jobId: string) => void }) {
  const [params, setParams] = useSearchParams();
  const [version, setVersion] = useArticleWorkflowVersion();
  const [mode, setMode] = useState<InputMode>(() => {
    if (params.get('input') === 'v3') return 'v3';
    const saved = window.localStorage.getItem(inputModeKey);
    return saved === 'v3' ? 'v3' : version;
  });
  useEffect(() => { window.localStorage.setItem(inputModeKey, mode); }, [mode]);
  useEffect(() => {
    if (params.get('input') === 'v3') {
      setMode('v3');
      setParams(previous => { previous.delete('input'); return previous; }, { replace: true });
    }
  }, [params, setParams]);
  const controls = <div role="group" aria-label="Workflow version" className="flex h-7 rounded-md border border-border-default bg-surface-subtle p-0.5">
    {(['v1', 'v3', 'v2'] as const).map(option => <button key={option} type="button" aria-pressed={mode === option}
      onClick={() => { setMode(option); if (option !== 'v3') setVersion(option); }}
      className={`min-w-10 rounded px-2 text-[10px] font-bold transition-colors ${mode === option ? 'bg-surface text-accent shadow-sm' : 'text-content-tertiary hover:text-content-primary'}`}>
      {option === 'v3' ? 'V2' : option === 'v2' ? 'V3' : 'V1'}
    </button>)}
  </div>;
  return <>
    <section aria-label="URL workflow input" hidden={mode === 'v3'}>
      <QuickRun version={version} versionControl={controls} onRunStarted={onRunStarted} />
    </section>
    <section aria-label="V2 manual input" hidden={mode !== 'v3'}>
      <ManualArticleRun versionControl={controls} onRunStarted={onRunStarted} />
    </section>
  </>;
}
