import React, { useState } from 'react';
import { X, CheckCircle, XCircle, Clock, Loader2, FileText, RefreshCw, Copy, ExternalLink } from 'lucide-react';
import { syncJob } from '../api/client';

const JobDetailsModal = ({ job: initialJob, onClose }) => {
  const [syncing, setSyncing] = useState(false);
  const job = initialJob; // We'll rely on parent polling to update the object via props

  if (!job) return null;

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncJob(job.id);
      // parent polling will pick up the update
    } catch (error) {
      alert('Failed to sync job status.');
    } finally {
      setSyncing(false);
    }
  };

  const handleCopy = async (value) => {
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
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-50 border-green-100';
      case 'failed': return 'text-red-600 bg-red-50 border-red-100';
      case 'partial_success': return 'text-amber-600 bg-amber-50 border-amber-100';
      default: return 'text-blue-600 bg-blue-50 border-blue-100';
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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className={`text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${getStatusColor(job.status)}`}>
                {job.status}
              </span>
              <span className="text-xs text-gray-400 font-mono">Job ID: {job.id}</span>
            </div>
            <div className="flex items-center gap-3 min-w-0">
              <h3 className="text-2xl font-bold text-gray-900 shrink-0">{job.pipeline_name || 'Pipeline Execution'}</h3>
              {inputUrl && (
                <div className="flex items-center gap-1 min-w-0 text-sm">
                  <a
                    href={inputUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="min-w-0 max-w-[320px] truncate font-mono text-blue-700 hover:text-blue-900"
                    title={inputUrl}
                  >
                    {inputUrl}
                  </a>
                  <button
                    type="button"
                    onClick={() => handleCopy(inputUrl)}
                    className="shrink-0 p-1.5 rounded-md text-gray-500 hover:text-gray-900 hover:bg-white border border-transparent hover:border-gray-200"
                    title="Copy input link"
                  >
                    <Copy size={14} />
                  </button>
                  <a
                    href={inputUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 p-1.5 rounded-md text-gray-500 hover:text-gray-900 hover:bg-white border border-transparent hover:border-gray-200"
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
                onClick={handleSync}
                disabled={syncing}
                title="Force Sync Status"
                className="p-2 hover:bg-blue-100 text-blue-600 rounded-full transition-colors"
              >
                <RefreshCw size={20} className={syncing ? 'animate-spin' : ''} />
              </button>
            )}
            <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-500">
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Progress Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
              <p className="text-xs font-bold text-gray-400 uppercase mb-1">Current Progress</p>
              <div className="flex items-center space-x-3">
                <span className="text-2xl font-bold text-gray-800">{job.progress}%</span>
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-600 transition-all duration-500" style={{ width: `${job.progress}%` }}></div>
                </div>
              </div>
            </div>
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
              <p className="text-xs font-bold text-gray-400 uppercase mb-1">Start Time</p>
              <div className="flex items-center space-x-2 text-gray-700">
                <Clock size={16} />
                <span className="font-semibold">{new Date(job.start_time).toLocaleString()}</span>
              </div>
            </div>
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
              <p className="text-xs font-bold text-gray-400 uppercase mb-1">Active Step</p>
              <div className="flex items-center space-x-2 text-gray-700">
                {job.status === 'running' && <Loader2 size={16} className="animate-spin text-blue-500" />}
                <span className="font-semibold">{job.current_step || (job.status === 'success' ? 'Finished' : 'None')}</span>
              </div>
            </div>
          </div>

          {/* Detailed Logs */}
          <div className="space-y-4">
            <h4 className="text-lg font-bold text-gray-800 flex items-center space-x-2">
              <FileText size={20} className="text-gray-400" />
              <span>Step Logs</span>
            </h4>

            <div className="space-y-3">
              {displayLogs.length === 0 ? (
                <div className="text-center py-10 text-gray-400 italic bg-gray-50 rounded-xl border border-dashed border-gray-200">
                  No detailed logs recorded for this job.
                </div>
              ) : (
                displayLogs.map((log, index) => (
                  <div key={index} className="flex space-x-4 group">
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                        log.event === 'error' || log.event === 'failed' ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'
                      }`}>
                        {log.event === 'error' || log.event === 'failed' ? <XCircle size={16} /> : <CheckCircle size={16} />}
                      </div>
                      {index !== displayLogs.length - 1 && <div className="w-0.5 h-full bg-gray-100 group-hover:bg-gray-200 transition-colors my-1"></div>}
                    </div>
                    <div className="flex-1 pb-6">
                      <div className="flex justify-between items-start mb-1">
                        <h5 className="font-bold text-gray-800">{log.step_name || 'Event'}</h5>
                        <span className="text-[10px] font-mono text-gray-400">{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}</span>
                      </div>
                      <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg border border-gray-100 font-mono break-all whitespace-pre-wrap">
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
        <div className="p-6 border-t border-gray-100 bg-gray-50/50 flex justify-end">
          <button 
            onClick={onClose}
            className="px-6 py-2 bg-gray-800 text-white rounded-xl font-bold hover:bg-black transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};

export default JobDetailsModal;
