import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Circle, Clock3, Loader2, XCircle } from 'lucide-react';

export type ProgressTimelineStep = {
  id: string;
  label: string;
};

type ProgressTimelineProps = {
  progress?: number;
  current?: string;
  status?: string;
  detail?: string;
  startedAt?: string;
  updatedAt?: string;
  failedStep?: string;
  cancelledStep?: string;
  steps?: ProgressTimelineStep[];
  logs?: WorkflowLog[];
  version?: 'V1' | 'V2';
};

export type WorkflowLog = {
  step_name?: string;
  detail?: string;
  timestamp?: string;
  event?: string;
  progress?: number;
};

const defaultSteps: ProgressTimelineStep[] = [
  { id: 'prepare', label: 'Prepare' },
  { id: 'generate', label: 'Generate' },
  { id: 'review', label: 'Review' },
  { id: 'wordpress', label: 'WordPress' },
];

function matchesStep(current: string | undefined, step: ProgressTimelineStep) {
  if (!current) return false;
  return current === step.id || current.toLowerCase().startsWith(step.label.toLowerCase());
}

function formatDuration(milliseconds: number) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m`;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function formatTimestamp(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function extractChunk(detail?: string) {
  const match = detail?.match(/\bchunk\s+(\d+)\s*(?:\/|of)\s*(\d+)\b/i);
  return match ? { current: Number(match[1]), total: Number(match[2]) } : null;
}

function displayStepName(value?: string) {
  const key = (value || '').toLowerCase();
  if (key.includes('rewrite') || key.includes('chunk')) return 'Story processing';
  if (key.includes('prepare_publish')) return 'Prepare publish';
  if (key.includes('publish_wordpress')) return 'Publish to WordPress';
  if (key.includes('choose_patterns')) return 'Choose story patterns';
  if (key.includes('agent')) return 'Generate story';
  return (value || 'Workflow update').replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase());
}

function isChildLog(log: WorkflowLog) {
  return /\bchunk\s*\d+\s*(?:\/|of)\s*\d+\b/i.test(log.detail || '')
    || /\bchunk\s*\d+\b/i.test(log.step_name || '')
    || /\bchunk\s*\d+\b/i.test(log.detail || '');
}

function formatLogDuration(logs: WorkflowLog[]) {
  const details = logs.map(log => log.detail || '').join(' ');
  const explicit = [...details.matchAll(/(?:·|in)\s*([\d,.]+)\s*(ms|s|sec|seconds)\b/gi)];
  if (explicit.length) {
    const milliseconds = explicit.reduce((total, match) => total + Number(match[1].replaceAll(',', '')) * (match[2].toLowerCase() === 'ms' ? 1 : 1000), 0);
    return milliseconds < 1000 ? `${Math.round(milliseconds)} ms` : `${(milliseconds / 1000).toFixed(1)} s`;
  }
  const timestamps = logs.map(log => Date.parse(log.timestamp || '')).filter(value => !Number.isNaN(value));
  if (timestamps.length > 1) return formatDuration(Math.max(0, Math.max(...timestamps) - Math.min(...timestamps)));
  return '';
}

function ExecutionLogTimeline({ logs, version, status }: { logs: WorkflowLog[]; version?: 'V1' | 'V2'; status: string }) {
  const groups = useMemo(() => {
    const result: Array<{ name: string; logs: WorkflowLog[]; children: WorkflowLog[] }> = [];
    logs.forEach(log => {
      const child = isChildLog(log);
      const name = displayStepName(log.step_name || log.detail);
      const target = child ? result.find(group => group.name === 'Story processing') || result.at(-1) : result.find(group => group.name === name);
      if (target) {
        (child ? target.children : target.logs).push(log);
      } else {
        result.push({ name, logs: child ? [] : [log], children: child ? [log] : [] });
      }
    });
    return result;
  }, [logs]);

  return <ol className="space-y-3" aria-label="Execution timeline">
    {groups.map((group, index) => {
      const allLogs = [...group.logs, ...group.children];
      const failed = allLogs.some(log => log.event === 'failed' || log.event === 'error');
      const active = index === groups.length - 1 && ['queued', 'pending', 'running'].includes(status);
      const done = !active && !failed;
      const Icon = failed ? XCircle : done ? CheckCircle2 : active ? Loader2 : Circle;
      return <li key={`${group.name}-${index}`} className="relative flex gap-3" aria-current={active ? 'step' : undefined}>
        <div className="flex w-7 shrink-0 flex-col items-center">
          <span className={`flex h-7 w-7 items-center justify-center rounded-full ${failed ? 'bg-status-danger/10 text-status-danger' : active ? 'bg-accent/10 text-accent' : done ? 'bg-status-success/10 text-status-success' : 'bg-surface-subtle text-content-tertiary'}`}><Icon size={16} className={active ? 'animate-spin' : ''} /></span>
          {index < groups.length - 1 && <span className="mt-1 h-full min-h-5 w-px bg-border-subtle" />}
        </div>
        <div className="min-w-0 flex-1 pb-2">
          <div className="flex items-start justify-between gap-3">
            <div><p className="font-semibold text-content-primary">{group.name}</p><p className="text-xs text-content-tertiary">{version || 'Workflow'} · {failed ? 'Failed' : active ? 'In progress' : done ? 'Completed' : 'Waiting'}</p></div>
            <span className="shrink-0 text-xs font-mono text-content-tertiary">{formatLogDuration(allLogs)}</span>
          </div>
          {group.logs.at(-1)?.detail && <p className="mt-2 rounded-lg border border-border-subtle bg-surface-subtle px-3 py-2 text-sm text-content-secondary">{group.logs.at(-1)?.detail}</p>}
          {group.children.length > 0 && <div className="mt-2 ml-3 space-y-1.5 border-l border-border-default pl-3">
            {group.children.map((child, childIndex) => <div key={`${child.timestamp || childIndex}-${child.detail}`} className="flex items-center justify-between gap-3 rounded-md bg-surface-subtle/70 px-2.5 py-2 text-xs"><span className="min-w-0 truncate text-content-secondary">{child.detail || 'Chunk update'}</span><span className="shrink-0 font-mono text-content-tertiary">{formatLogDuration([child])}</span></div>)}
          </div>}
        </div>
      </li>;
    })}
  </ol>;
}

function statusCopy(status: string, progress: number) {
  if (status === 'success') return { label: 'Completed', tone: 'success' };
  if (status === 'failed') return { label: 'Failed', tone: 'danger' };
  if (status === 'cancelled') return { label: 'Cancelled', tone: 'warning' };
  if (status === 'partial_success') return { label: 'Partially completed', tone: 'warning' };
  if (status === 'queued' || status === 'pending') return { label: 'Queued', tone: 'warning' };
  return { label: `Running · ${Math.round(progress)}%`, tone: 'running' };
}

export function ProgressTimeline({
  progress = 0,
  current,
  status = 'queued',
  detail,
  startedAt,
  updatedAt,
  failedStep,
  cancelledStep,
  steps = defaultSteps,
  logs,
  version,
}: ProgressTimelineProps) {
  const isLive = status === 'queued' || status === 'pending' || status === 'running';
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!isLive || !startedAt) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [isLive, startedAt]);

  const activeStep = steps.findIndex(step => matchesStep(current, step));
  const terminalStep = status === 'failed' ? failedStep : status === 'cancelled' ? cancelledStep : undefined;
  const terminalIndex = steps.findIndex(step => matchesStep(terminalStep, step));
  const progressionIndex = activeStep >= 0 ? activeStep : terminalIndex;
  const chunk = extractChunk(detail);
  const elapsed = useMemo(() => {
    if (!startedAt) return '—';
    const end = isLive ? now : (updatedAt ? new Date(updatedAt).getTime() : now);
    const start = new Date(startedAt).getTime();
    return Number.isNaN(start) ? '—' : formatDuration(Math.max(0, end - start));
  }, [isLive, now, startedAt, updatedAt]);
  const copy = statusCopy(status, progress);
  const currentLabel = progressionIndex >= 0 ? steps[progressionIndex].label : status === 'success' ? 'All steps finished' : 'Waiting for step update';
  const currentDetail = detail || (status === 'queued' ? 'Waiting for the worker to start' : 'Processing workflow');
  const lastUpdate = formatTimestamp(updatedAt);
  const toneClasses = {
    success: 'border-status-success/30 bg-status-success/10 text-status-success',
    danger: 'border-status-danger/30 bg-status-danger/10 text-status-danger',
    warning: 'border-status-warning/30 bg-status-warning/10 text-status-warning',
    running: 'border-accent/30 bg-accent/10 text-accent',
  }[copy.tone];

  return <section aria-label="Workflow progress" aria-live="polite" className="space-y-4">
    <div className={`rounded-xl border p-4 ${toneClasses}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
            <span>{copy.label}</span>
            <span className="text-content-tertiary">·</span>
            <span className="text-content-secondary">Step {progressionIndex >= 0 ? progressionIndex + 1 : status === 'success' ? steps.length : '—'} of {steps.length}</span>
          </div>
          <p className="mt-1 truncate text-sm text-content-primary">{currentLabel}</p>
          <p className="mt-1 text-xs text-content-secondary">{currentDetail}</p>
        </div>
        <div className="flex shrink-0 items-center gap-3 text-xs text-content-secondary">
          {chunk && <span className="rounded-md bg-surface px-2 py-1 font-medium">Chunk {chunk.current} / {chunk.total}</span>}
          <span className="inline-flex items-center gap-1"><Clock3 size={13} /> {elapsed}</span>
        </div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface/70" aria-label={`${Math.round(progress)} percent complete`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
        <div className={`h-full rounded-full transition-[width] duration-300 ${status === 'failed' ? 'bg-status-danger' : status === 'cancelled' ? 'bg-status-warning' : status === 'success' ? 'bg-status-success' : 'bg-accent'}`} style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap justify-between gap-2 text-[11px] text-content-tertiary">
        <span>{lastUpdate ? `Last update ${lastUpdate}` : 'Waiting for first update'}</span>
        <span>{Math.round(progress)}% complete</span>
      </div>
    </div>

    {logs?.length ? <ExecutionLogTimeline logs={logs} version={version} status={status} /> : <ol className="space-y-2" aria-label="Workflow steps">
      {steps.map((step, index) => {
        const isTerminalError = (status === 'failed' || status === 'cancelled') && index === terminalIndex;
        const done = status === 'success' || (progressionIndex >= 0 && index < progressionIndex && !isTerminalError);
        const active = status === 'running' && index === activeStep;
        const Icon = isTerminalError ? XCircle : done ? CheckCircle2 : active ? Loader2 : Circle;
        const label = active && detail ? detail : step.label;
        const stateLabel = isTerminalError ? (status === 'failed' ? 'Failed' : 'Cancelled') : done ? 'Done' : active ? 'In progress' : 'Not started';
        const terminalTone = status === 'cancelled' ? 'border-status-warning/30 bg-status-warning/5 text-status-warning' : 'border-status-danger/30 bg-status-danger/5 text-status-danger';
        const tone = isTerminalError ? terminalTone : active ? 'border-accent/30 bg-accent/5 text-content-primary' : done ? 'border-status-success/20 bg-status-success/5 text-content-primary' : 'border-border-default bg-surface';
        return <li key={step.id} className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${tone}`} aria-current={active ? 'step' : undefined}>
          <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${isTerminalError ? status === 'cancelled' ? 'bg-status-warning/10 text-status-warning' : 'bg-status-danger/10 text-status-danger' : done ? 'bg-status-success/10 text-status-success' : active ? 'bg-accent/10 text-accent' : 'bg-surface-subtle text-content-tertiary'}`}>
            <Icon size={16} className={active ? 'animate-spin' : ''} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-medium">{label}</span>
            {active && chunk && <span className="mt-0.5 block text-xs text-content-secondary">Chunk {chunk.current} of {chunk.total}</span>}
          </span>
          <span className={`shrink-0 text-xs font-medium ${isTerminalError ? status === 'cancelled' ? 'text-status-warning' : 'text-status-danger' : done ? 'text-status-success' : active ? 'text-accent' : 'text-content-tertiary'}`}>{stateLabel}</span>
        </li>;
      })}
    </ol>}
  </section>;
}
