import React from 'react';
import { Clock, Loader2, Copy, ExternalLink, RotateCw, XCircle } from 'lucide-react';
import { Job } from '../../../api/types';
import { Card, CardHeader, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { cn } from '../../../lib/utils';

interface JobExtended extends Job {
  pipeline_name?: string;
  start_time: string;
  current_step?: string;
  progress: number;
  logs?: any[];
  rerun_at?: string | null;
  rerun_job_id?: string | null;
}

interface JobCardProps {
  job: JobExtended;
  onClick: () => void;
  onRerun?: () => void;
  isRerunning?: boolean;
  onCancel?: () => void;
  isCancelling?: boolean;
}

const JobCard: React.FC<JobCardProps> = ({ job, onClick, onRerun, isRerunning = false, onCancel, isCancelling = false }) => {
  const isQueued = job.status === 'queued';
  const isRunning = job.status === 'running';
  const isSuccess = job.status === 'success';
  const isPartialSuccess = job.status === 'partial_success';
  const isFailed = job.status === 'failed';
  const isCancelled = job.status === 'cancelled';
  const canCancel = isQueued || isRunning;

  const formatTime = (isoString: string) => {
    if (!isoString) return '--:--';
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const logs = Array.isArray(job.logs) ? job.logs : [];
  const inputLog = logs.find((log) => log.event === 'input' && log.url);
  const stepOneLog = logs.find((log) => (
    log.step_name === 'Extract article from URL'
    && typeof log.detail === 'string'
    && log.detail.includes('Step 1: Extracting article from ')
  ));
  const inputUrl = job.input_type === 'url'
    ? job.input_text || ''
    : inputLog?.url || stepOneLog?.detail?.split('Step 1: Extracting article from ')[1]?.trim() || '';
  const hasBeenRerun = Boolean(job.rerun_job_id || job.rerun_at);

  const handleCopy = async (event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      await navigator.clipboard.writeText(inputUrl);
    } catch (error) {
      const textarea = document.createElement('textarea');
      textarea.value = inputUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
  };

  const handleRerun = (event: React.MouseEvent) => {
    event.stopPropagation();
    if (!onRerun || hasBeenRerun || isRerunning) return;
    onRerun();
  };

  const handleCancel = (event: React.MouseEvent) => {
    event.stopPropagation();
    if (!onCancel || !canCancel || isCancelling) return;
    onCancel();
  };

  return (
    <Card 
      onClick={onClick}
      className={cn(
        "cursor-pointer transition-all hover:shadow-md hover:scale-[1.01] active:scale-[0.99] border-border-default",
        isQueued && "border-status-warning/50 bg-status-warning/5",
        isRunning && "border-accent/50 bg-accent/5",
        isFailed && "border-status-danger/50"
      )}
    >
      <CardHeader className="p-5 pb-3">
        <div className="flex justify-between items-start w-full">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={cn(
                "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded",
                isQueued ? "bg-status-warning/10 text-status-warning" :
                isRunning ? "bg-accent/10 text-accent" :
                isSuccess ? "bg-status-success/10 text-status-success" :
                isPartialSuccess ? "bg-status-warning/10 text-status-warning" :
                isCancelled ? "bg-orange-100 text-orange-700" :
                isFailed ? "bg-status-danger/10 text-status-danger" : "bg-surface-subtle text-content-secondary"
              )}>
                {job.status.replace('_', ' ')}
              </span>
              <span className="text-[10px] text-content-tertiary font-mono">#{job.id.slice(0, 8)}</span>
            </div>
            <h4 className="font-bold text-content-primary truncate mt-1 text-sm">{job.pipeline_name || 'Pipeline Run'}</h4>
          </div>
          <div className="shrink-0 flex items-center gap-2 text-content-tertiary">
            {canCancel && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={isCancelling}
                onClick={handleCancel}
                className="h-7 w-7 text-content-tertiary hover:text-status-danger hover:bg-status-danger/10"
                title="Cancel job"
              >
                {isCancelling ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
              </Button>
            )}
            <div className="flex items-center gap-1">
              <Clock size={12} />
              <span className="text-[10px] font-bold font-mono">{formatTime(job.start_time)}</span>
            </div>
          </div>
        </div>

        {inputUrl && (
          <div className="flex items-center gap-1 mt-2 p-1.5 bg-canvas rounded border border-border-default min-w-0">
            <span className="truncate text-[10px] font-mono text-accent flex-1" title={inputUrl}>
              {inputUrl}
            </span>
            <div className="flex shrink-0">
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5 text-content-tertiary hover:text-content-primary"
                onClick={handleCopy}
              >
                <Copy size={10} />
              </Button>
              <a
                href={inputUrl}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="h-5 w-5 flex items-center justify-center text-content-tertiary hover:text-content-primary hover:bg-surface-subtle rounded"
              >
                <ExternalLink size={10} />
              </a>
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="p-5 pt-0 space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between items-end text-[11px]">
            <span className="text-content-secondary font-medium">
              {isQueued ? (
                <span className="text-status-warning font-bold">Queued</span>
              ) : isRunning ? (
                <span className="flex items-center space-x-1 text-accent animate-pulse">
                  <Loader2 size={12} className="animate-spin" />
                  <span className="truncate max-w-[150px]">{job.current_step || 'Processing...'}</span>
                </span>
              ) : isSuccess ? (
                <span className="text-status-success font-bold">Success</span>
              ) : isPartialSuccess ? (
                <span className="text-status-warning font-bold">Partial Success</span>
              ) : isCancelled ? (
                <span className="text-orange-700 font-bold">Cancelled</span>
              ) : (
                <span className="text-status-danger font-bold">Failed</span>
              )}
            </span>
            <span className="font-bold text-content-primary">{job.progress}%</span>
          </div>

          <div className="w-full bg-surface-subtle rounded-full h-2 overflow-hidden shadow-inner">
            <div 
              className={cn(
                "h-full transition-all duration-700 ease-out rounded-full",
                isQueued ? "bg-status-warning" : isRunning ? "bg-accent" : isSuccess ? "bg-status-success" : isPartialSuccess ? "bg-status-warning" : isCancelled ? "bg-orange-500" : "bg-status-danger"
              )}
              style={{ width: `${job.progress}%` }}
            ></div>
          </div>
        </div>

        {isFailed && job.logs && job.logs.length > 0 && (
          <div className="mt-2 text-[10px] text-status-danger bg-status-danger/10 p-2.5 rounded-lg border border-status-danger/20 leading-relaxed font-medium line-clamp-2">
            {job.logs[job.logs.length - 1].detail || 'Unknown internal error occurred'}
          </div>
        )}

        {isFailed && (
          <div className="flex items-center justify-between gap-3 pt-1">
            {hasBeenRerun ? (
              <span className="text-[10px] font-bold uppercase tracking-wider text-content-tertiary">
                {job.rerun_job_id ? `Rerun queued #${job.rerun_job_id.slice(0, 8)}` : 'Rerun queued'}
              </span>
            ) : (
              <span className="text-[10px] text-content-tertiary">
                Ready to retry with the same input.
              </span>
            )}
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={hasBeenRerun || isRerunning}
              onClick={handleRerun}
              className="h-8 px-3 shrink-0"
            >
              <RotateCw size={13} className={cn("mr-1.5", isRerunning && "animate-spin")} />
              <span className="text-xs font-bold">{hasBeenRerun ? 'Queued' : isRerunning ? 'Running' : 'Rerun'}</span>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default JobCard;
