import React, { useState } from 'react';
import { X, CheckCircle, XCircle, Clock, Loader2, FileText, RefreshCw, Copy, ExternalLink } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { syncJob } from '../../../api/client';
import { Job } from '../../../api/types';

interface JobExtended extends Job {
  pipeline_name?: string;
  start_time: string;
  current_step?: string;
  progress: number;
  logs?: any[];
}

interface JobDetailsModalProps {
  job: JobExtended;
  onClose: () => void;
}

const JobDetailsModal: React.FC<JobDetailsModalProps> = ({ job, onClose }) => {
  const syncMutation = useMutation({
    mutationFn: () => syncJob(job.id),
    onError: () => alert('Failed to sync job status.'),
  });

  const handleCopy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
    } catch (error) {
      const textarea = document.createElement('textarea');
      textarea.value = value;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
  };
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-status-success bg-status-success/10 border-status-success/20';
      case 'failed': return 'text-status-danger bg-status-danger/10 border-status-danger/20';
      case 'cancelled': return 'text-orange-700 bg-orange-100 border-orange-200';
      default: return 'text-accent bg-accent/10 border-accent/20';
    }
  };

  const logs = Array.isArray(job.logs) ? job.logs : [];
  const displayLogs = logs.filter((log) => log.detail && log.detail !== 'working' && log.event !== 'input');
  const inputLog = logs.find((log) => log.event === 'input' && log.url);
  const stepOneLog = logs.find((log) => (
    log.step_name === 'Extract article from URL'
    && typeof log.detail === 'string'
    && log.detail.includes('Step 1: Extracting article from ')
  ));
  const inputUrl = inputLog?.url || stepOneLog?.detail?.split('Step 1: Extracting article from ')[1]?.trim() || '';

  return (
    <div className="fixed inset-0 z-50 flex justify-center items-end sm:items-center p-0 sm:p-4">
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      <div className="relative w-full max-w-3xl bg-surface rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[90vh] overflow-hidden flex flex-col border border-border-default animate-slide-up sm:animate-none">
        {/* Mobile Pull Indicator */}
        <div className="w-full flex justify-center py-2 sm:hidden bg-surface absolute top-0 z-10" onClick={onClose}>
          <div className="w-12 h-1.5 bg-border-strong rounded-full"></div>
        </div>

        {/* Header */}
        <div className="p-6 pt-8 sm:pt-6 border-b border-border-subtle flex justify-between items-center bg-surface shrink-0">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className={`text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${getStatusColor(job.status)}`}>
                {job.status}
              </span>
              <span className="text-xs text-content-tertiary font-mono">Job ID: {job.id}</span>
            </div>
            <div className="flex items-center gap-3 min-w-0">
              <h3 className="text-2xl font-bold text-content-primary shrink-0">{job.pipeline_name || 'Pipeline Execution'}</h3>
              {inputUrl && (
                <div className="flex items-center gap-1 min-w-0 text-sm">
                  <a
                    href={inputUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="min-w-0 max-w-[320px] truncate font-mono text-accent hover:underline"
                    title={inputUrl}
                  >
                    {inputUrl}
                  </a>
                  <button
                    type="button"
                    onClick={() => handleCopy(inputUrl)}
                    className="shrink-0 p-1.5 rounded-md text-content-tertiary hover:text-content-primary hover:bg-surface-subtle border border-transparent hover:border-border-default"
                    title="Copy input link"
                  >
                    <Copy size={14} />
                  </button>
                  <a
                    href={inputUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 p-1.5 rounded-md text-content-tertiary hover:text-content-primary hover:bg-surface-subtle border border-transparent hover:border-border-default"
                    title="Open input link"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {job.status === 'running' && (
              <button 
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                title="Force Sync Status"
                className="p-2 hover:bg-accent/10 text-accent rounded-full transition-colors"
              >
                <RefreshCw size={20} className={syncMutation.isPending ? 'animate-spin' : ''} />
              </button>
            )}
            <button onClick={onClose} className="p-2 hover:bg-surface-subtle rounded-full transition-colors text-content-tertiary">
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Progress Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-surface-subtle p-4 rounded-xl border border-border-subtle">
              <p className="text-xs font-bold text-content-tertiary uppercase mb-1">Current Progress</p>
              <div className="flex items-center space-x-3">
                <span className="text-2xl font-bold text-content-primary">{job.progress}%</span>
                <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden border border-border-default">
                  <div className="h-full bg-accent transition-all duration-500" style={{ width: `${job.progress}%` }}></div>
                </div>
              </div>
            </div>
            <div className="bg-surface-subtle p-4 rounded-xl border border-border-subtle">
              <p className="text-xs font-bold text-content-tertiary uppercase mb-1">Start Time</p>
              <div className="flex items-center space-x-2 text-content-secondary">
                <Clock size={16} />
                <span className="font-semibold">{new Date(job.start_time).toLocaleString()}</span>
              </div>
            </div>
            <div className="bg-surface-subtle p-4 rounded-xl border border-border-subtle">
              <p className="text-xs font-bold text-content-tertiary uppercase mb-1">Active Step</p>
              <div className="flex items-center space-x-2 text-content-secondary">
                {job.status === 'running' && <Loader2 size={16} className="animate-spin text-accent" />}
                <span className="font-semibold">{job.current_step || (job.status === 'queued' ? 'Queued' : job.status === 'success' ? 'Finished' : job.status === 'cancelled' ? 'Cancelled' : 'None')}</span>
              </div>
            </div>
          </div>

          {/* Detailed Logs */}
          <div className="space-y-4">
            <h4 className="text-lg font-bold text-content-primary flex items-center space-x-2">
              <FileText size={20} className="text-content-tertiary" />
              <span>Step Logs</span>
            </h4>

            <div className="space-y-3">
              {displayLogs.length === 0 ? (
                <div className="text-center py-10 text-content-tertiary italic bg-surface-subtle rounded-xl border border-dashed border-border-default">
                  No detailed logs recorded for this job.
                </div>
              ) : (
                displayLogs.map((log, index) => (
                  <div key={index} className="flex space-x-4 group">
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                        log.event === 'error' || log.event === 'failed' ? 'bg-status-danger/10 text-status-danger' : 'bg-status-success/10 text-status-success'
                      }`}>
                        {log.event === 'error' || log.event === 'failed' ? <XCircle size={16} /> : <CheckCircle size={16} />}
                      </div>
                      {index !== displayLogs.length - 1 && <div className="w-0.5 h-full bg-border-subtle group-hover:bg-border-default transition-colors my-1"></div>}
                    </div>
                    <div className="flex-1 pb-6">
                      <div className="flex justify-between items-start mb-1">
                        <h5 className="font-bold text-content-primary">{log.step_name || 'Event'}</h5>
                        <span className="text-[10px] font-mono text-content-tertiary">{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}</span>
                      </div>
                      <p className="text-sm text-content-secondary bg-surface-subtle p-3 rounded-lg border border-border-subtle font-mono break-all whitespace-pre-wrap">
                        {log.detail}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
        
        {/* Footer */}
        <div className="p-6 border-t border-border-subtle bg-surface flex justify-end">
          <button 
            onClick={onClose}
            className="px-6 py-2 bg-[var(--button-primary-bg)] text-[var(--button-primary-text)] rounded-md text-sm font-medium shadow hover:bg-[var(--button-primary-bg-hover)] transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};

export default JobDetailsModal;
