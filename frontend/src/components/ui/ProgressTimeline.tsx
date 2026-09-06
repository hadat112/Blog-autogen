import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

export function ProgressTimeline({ progress, current }: { progress: number; current?: string }) {
  const steps = ['Prepare', 'Generate', 'Review', 'WordPress'];
  return <div aria-live="polite" className="space-y-2">
    {steps.map((step, index) => {
      const threshold = index * 25;
      const done = progress >= threshold + 25;
      const active = progress >= threshold && !done;
      const Icon = done ? CheckCircle2 : active ? Loader2 : Circle;
      return <div key={step} className={`flex items-center gap-2 text-sm ${done || active ? 'text-content-primary' : 'text-content-tertiary'}`}><Icon size={16} className={active ? 'animate-spin text-accent' : done ? 'text-status-success' : ''} /><span>{active && current ? current : step}</span></div>;
    })}
  </div>;
}
