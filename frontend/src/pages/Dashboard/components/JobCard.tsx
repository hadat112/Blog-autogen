import React from 'react';
import { Clock, Loader2, Copy, ExternalLink } from 'lucide-react';
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
}

interface JobCardProps {
  job: JobExtended;
  onClick: () => void;
}

const JobCard: React.FC<JobCardProps> = ({ job, onClick }) => {
  const isRunning = job.status === 'running';
  const isSuccess = job.status === 'success';
  const isFailed = job.status === 'failed';

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
  const inputUrl = inputLog?.url || stepOneLog?.detail?.split('Step 1: Extracting article from ')[1]?.trim() || '';

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

  return (
    <Card 
      onClick={onClick}
      className={cn(
        "cursor-pointer transition-all hover:shadow-md hover:scale-[1.01] active:scale-[0.99] border-border-default",
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
                isRunning ? "bg-accent/10 text-accent" : 
                isSuccess ? "bg-status-success/10 text-status-success" : 
                isFailed ? "bg-status-danger/10 text-status-danger" : "bg-surface-subtle text-content-secondary"
              )}>
                {job.status.replace('_', ' ')}
              </span>
              <span className="text-[10px] text-content-tertiary font-mono">#{job.id.slice(0, 8)}</span>
            </div>
            <h4 className="font-bold text-content-primary truncate mt-1 text-sm">{job.pipeline_name || 'Pipeline Run'}</h4>
          </div>
          <div className="shrink-0 flex items-center gap-1 text-content-tertiary">
            <Clock size={12} />
            <span className="text-[10px] font-bold font-mono">{formatTime(job.start_time)}</span>
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
              {isRunning ? (
                <span className="flex items-center space-x-1 text-accent animate-pulse">
                  <Loader2 size={12} className="animate-spin" />
                  <span className="truncate max-w-[150px]">{job.current_step || 'Processing...'}</span>
                </span>
              ) : isSuccess ? (
                <span className="text-status-success font-bold">Success</span>
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
                isRunning ? "bg-accent" : isSuccess ? "bg-status-success" : "bg-status-danger"
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
      </CardContent>
    </Card>
  );
};

export default JobCard;
