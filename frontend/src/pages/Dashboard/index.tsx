import React, { useEffect, useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { cancelJob, getJobs, runPipeline } from '../../api/client';
import { startArticleWorkflow, startRewrite } from '../../api/workflows';
import QuickRun from './components/QuickRun';
import JobCard from './components/JobCard';
import JobDetailsModal from './components/JobDetailsModal';
import DashboardSkeleton from './components/DashboardSkeleton';
import { History, Activity } from 'lucide-react';
import { Job } from '../../api/types';
import { Select } from '../../components/ui/Select';

const getJobInput = (job: Job) => {
  if (job.input_text?.trim()) return job.input_text.trim();

  const logs = Array.isArray(job.logs) ? job.logs : [];
  const inputLog = logs.find((log) => log.event === 'input' && log.detail);
  if (inputLog?.detail) return inputLog.detail;

  const prefix = 'Step 1: Extracting article from ';
  const stepOneLog = logs.find((log) => (
    log.step_name === 'Extract article from URL'
    && typeof log.detail === 'string'
    && log.detail.includes(prefix)
  ));

  return stepOneLog?.detail?.split(prefix)[1]?.trim() || '';
};

const Dashboard = () => {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [rerunningJobId, setRerunningJobId] = useState<string | null>(null);
  const [cancellingJobId, setCancellingJobId] = useState<string | null>(null);
  const [workflowFilter, setWorkflowFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [activePage, setActivePage] = useState(1);
  const [historyPage, setHistoryPage] = useState(1);

  const activeQuery = useQuery({
    queryKey: ['jobs', 'active', activePage, workflowFilter, statusFilter],
    queryFn: async () => {
      const { data } = await getJobs({ page: activePage, page_size: 9, workflow_type: workflowFilter, status_group: 'active', status: statusFilter === 'all' ? undefined : statusFilter as 'success' | 'failed' | 'cancelled' });
      return data;
    },
    placeholderData: keepPreviousData,
    staleTime: 1000,
    refetchInterval: 3000, // Poll every 3 seconds
  });
  const historyQuery = useQuery({
    queryKey: ['jobs', 'history', historyPage, workflowFilter, statusFilter],
    queryFn: async () => {
      const { data } = await getJobs({ page: historyPage, page_size: 9, workflow_type: workflowFilter, status_group: 'history', status: statusFilter === 'all' ? undefined : statusFilter as 'success' | 'failed' | 'cancelled' });
      return data;
    },
    placeholderData: keepPreviousData,
    staleTime: 3000,
    refetchInterval: 3000, // Keep recent activity in sync when active jobs finish
  });

  const activeJobs = activeQuery.data?.items ?? [];
  const historyJobs = historyQuery.data?.items ?? [];
  const jobs = [...activeJobs, ...historyJobs];

  useEffect(() => {
    if (activeQuery.data && activeQuery.data.total_pages > 0 && activePage > activeQuery.data.total_pages) {
      setActivePage(activeQuery.data.total_pages);
    }
    if (historyQuery.data && historyQuery.data.total_pages > 0 && historyPage > historyQuery.data.total_pages) {
      setHistoryPage(historyQuery.data.total_pages);
    }
  }, [activeQuery.data, activePage, historyQuery.data, historyPage]);

  const refetch = () => Promise.all([activeQuery.refetch(), historyQuery.refetch()]);

  const isSourceProxyEnabled = () => window.localStorage.getItem('story-autogen-source-proxy') === 'true';

  const rerunMutation = useMutation({
    mutationFn: (job: Job) => {
      const prompt = getJobInput(job);
      if (!prompt) {
        throw new Error('Job input was not found in logs');
      }
      if (job.workflow_type === 'article_v2' || job.workflow_type === 'rewrite') {
        return startArticleWorkflow(job.pipeline_id, prompt, 'v2', isSourceProxyEnabled(), job.id);
      }
      if (job.workflow_type === 'article_v1') {
        return startArticleWorkflow(job.pipeline_id, prompt, 'v1', isSourceProxyEnabled(), job.id);
      }
      return runPipeline(job.pipeline_id, { prompt, rerun_from_job_id: job.id });
    },
    onMutate: (job) => setRerunningJobId(job.id),
    onSuccess: () => refetch(),
    onError: (error: any) => {
      alert('Failed to rerun job: ' + (error.response?.data?.detail || error.message));
    },
    onSettled: () => setRerunningJobId(null),
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => cancelJob(jobId),
    onMutate: (jobId) => setCancellingJobId(jobId),
    onSuccess: () => refetch(),
    onError: (error: any) => {
      alert('Failed to cancel job: ' + (error.response?.data?.detail || error.message));
    },
    onSettled: () => setCancellingJobId(null),
  });

  const selectedJob = jobs.find(j => j.id === selectedJobId);

  if (activeQuery.isLoading && historyQuery.isLoading && jobs.length === 0) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-8">
      <QuickRun onRunStarted={() => refetch()} />

      <div className="flex flex-col justify-end gap-3 sm:flex-row"><label className="w-full max-w-xs text-sm font-medium text-content-secondary">Workflow filter<Select className="mt-1" value={workflowFilter} onChange={event => { setWorkflowFilter(event.target.value); setActivePage(1); setHistoryPage(1); }}><option value="all">All workflows</option><option value="legacy">V1</option><option value="rewrite">V2</option><option value="generate_story">Generate Story</option><option value="pattern_analysis">Pattern Analysis</option><option value="wp_publish">WordPress Publisher</option></Select></label><label className="w-full max-w-xs text-sm font-medium text-content-secondary">Status filter<Select className="mt-1" value={statusFilter} onChange={event => { setStatusFilter(event.target.value); setActivePage(1); setHistoryPage(1); }}><option value="all">All statuses</option><option value="success">Success</option><option value="failed">Error</option><option value="cancelled">Cancelled</option></Select></label></div>

      <div className="space-y-4">
        <h3 className="text-xl font-bold text-content-primary flex items-center space-x-2">
          <Activity size={20} className="text-accent" />
          <span>Active Tasks</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          {activeJobs.length === 0 ? (
            <div className="col-span-full py-12 text-center bg-canvas rounded-xl border border-dashed border-border-default">
              <p className="text-content-tertiary text-sm italic">No active tasks at the moment.</p>
            </div>
          ) : (
            activeJobs.map(job => (
              <JobCard
                key={job.id}
                job={job as any}
                onClick={() => setSelectedJobId(job.id)}
                onRerun={() => rerunMutation.mutate(job)}
                isRerunning={rerunningJobId === job.id}
                onCancel={() => cancelMutation.mutate(job.id)}
                isCancelling={cancellingJobId === job.id}
              />
            ))
          )}
        </div>
        {activeQuery.data && activeQuery.data.total > 0 && <Pagination page={activePage} pageData={activeQuery.data} onPageChange={setActivePage} />}
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-bold text-content-primary flex items-center space-x-2">
          <History size={20} className="text-content-tertiary" />
          <span>Recent Activity</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          {historyJobs.length === 0 ? (
            <div className="col-span-full py-12 text-center bg-canvas rounded-xl border border-dashed border-border-default">
              <p className="text-content-tertiary text-sm">No activity history yet.</p>
            </div>
          ) : (
            historyJobs.map(job => (
              <JobCard
                key={job.id}
                job={job as any}
                onClick={() => setSelectedJobId(job.id)}
                onRerun={() => rerunMutation.mutate(job)}
                isRerunning={rerunningJobId === job.id}
                onCancel={() => cancelMutation.mutate(job.id)}
                isCancelling={cancellingJobId === job.id}
              />
            ))
          )}
        </div>
        {historyQuery.data && historyQuery.data.total > 0 && <Pagination page={historyPage} pageData={historyQuery.data} onPageChange={setHistoryPage} />}
      </div>

      {selectedJob && (
        <JobDetailsModal 
          job={selectedJob as any} 
          onClose={() => setSelectedJobId(null)} 
        />
      )}
    </div>
  );
};

export default Dashboard;

function Pagination({ page, pageData, onPageChange }: { page: number; pageData: { page_size: number; total: number; total_pages: number }; onPageChange: (page: number) => void }) {
  return <div className="mt-4 flex flex-col items-center justify-between gap-3 border-t border-border-default pt-4 sm:flex-row">
    <p className="text-xs text-content-tertiary">Showing {(page - 1) * pageData.page_size + 1}-{Math.min(page * pageData.page_size, pageData.total)} of {pageData.total}</p>
    <div className="flex items-center gap-2">
      <button type="button" className="rounded-md border border-border-default px-3 py-1.5 text-xs font-semibold text-content-secondary hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-50" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
      <span className="text-xs font-semibold text-content-secondary">Page {page} of {pageData.total_pages}</span>
      <button type="button" className="rounded-md border border-border-default px-3 py-1.5 text-xs font-semibold text-content-secondary hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-50" disabled={page >= pageData.total_pages} onClick={() => onPageChange(page + 1)}>Next</button>
    </div>
  </div>;
}
