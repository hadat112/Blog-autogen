import React from 'react';
import { Clock, Loader2, Copy, ExternalLink } from 'lucide-react';

const JobCard = ({ job, onClick }) => {
  const isRunning = job.status === 'running';
  const isSuccess = job.status === 'success';
  const isPartial = job.status === 'partial_success';
  const isFailed = job.status === 'failed';

  const formatTime = (isoString) => {
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

  const handleCopy = async (event) => {
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
    <div 
      onClick={onClick}
      className={`bg-white p-5 rounded-xl shadow-sm border cursor-pointer transition-all hover:shadow-md hover:scale-[1.02] active:scale-[0.98] ${
        isRunning ? 'border-blue-200 bg-blue-50/10' : 
        isPartial ? 'border-amber-200 bg-amber-50/10' : 'border-gray-100'
      }`}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center space-x-2">
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
              isRunning ? 'bg-blue-100 text-blue-700' : 
              isSuccess ? 'bg-green-100 text-green-700' : 
              isPartial ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
            }`}>
              {job.status.replace('_', ' ')}
            </span>
            <span className="text-xs text-gray-400 font-mono">#{job.id.slice(0, 8)}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 min-w-0">
            <h4 className="font-bold text-gray-900 shrink-0">{job.pipeline_name || 'Pipeline Run'}</h4>
            {inputUrl && (
              <div className="flex items-center gap-1 min-w-0">
                <span className="max-w-[180px] truncate text-xs font-mono text-blue-700" title={inputUrl}>
                  {inputUrl}
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="shrink-0 p-1 rounded text-gray-400 hover:text-gray-800 hover:bg-gray-100"
                  title="Copy input link"
                >
                  <Copy size={12} />
                </button>
                <a
                  href={inputUrl}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(event) => event.stopPropagation()}
                  className="shrink-0 p-1 rounded text-gray-400 hover:text-gray-800 hover:bg-gray-100"
                  title="Open input link"
                >
                  <ExternalLink size={12} />
                </a>
              </div>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-tight flex items-center justify-end space-x-1">
            <Clock size={10} />
            <span>{formatTime(job.start_time)}</span>
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-500 italic">
            {isRunning ? (
              <span className="flex items-center space-x-1">
                <Loader2 size={12} className="animate-spin" />
                <span>{job.current_step || 'Initializing...'}</span>
              </span>
            ) : isSuccess ? 'Completed successfully' : 'Execution failed'}
          </span>
          <span className="font-bold text-gray-700">{job.progress}%</span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
          <div 
            className={`h-full transition-all duration-500 ease-out ${
              isRunning ? 'bg-blue-600' : 
              isSuccess ? 'bg-green-600' : 'bg-red-600'
            }`}
            style={{ width: `${job.progress}%` }}
          ></div>
        </div>

        {isFailed && job.logs && job.logs.length > 0 && (
          <p className="text-[10px] text-red-500 bg-red-50 p-2 rounded border border-red-100 line-clamp-2">
            Error: {job.logs[job.logs.length - 1].detail || 'Unknown error'}
          </p>
        )}
      </div>
    </div>
  );
};

export default JobCard;
