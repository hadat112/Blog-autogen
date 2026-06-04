import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { cancelJob, getJobs, runPipeline } from '../../api/client';
import QuickRun from './components/QuickRun';
import JobCard from './components/JobCard';
import JobDetailsModal from './components/JobDetailsModal';
import DashboardSkeleton from './components/DashboardSkeleton';
import { History, Activity } from 'lucide-react';
import { Job } from '../../api/types';

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

  const { data: jobs = [], isLoading, refetch } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const { data } = await getJobs();
      return data;
    },
    refetchInterval: 3000, // Poll every 3 seconds
  });

  const rerunMutation = useMutation({
    mutationFn: (job: Job) => {
      const prompt = getJobInput(job);
      if (!prompt) {
        throw new Error('Job input was not found in logs');
      }
      return runPipeline(job.pipeline_id, {
        prompt,
        rerun_from_job_id: job.id,
      });
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

  const runningJobs = jobs.filter(j => j.status === 'running' || j.status === 'queued');
  const pastJobs = jobs.filter(j => j.status !== 'running' && j.status !== 'queued').slice(0, 10);
  const selectedJob = jobs.find(j => j.id === selectedJobId);

  if (isLoading && jobs.length === 0) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-8">
      <QuickRun onRunStarted={() => refetch()} />

      <div className="space-y-4">
        <h3 className="text-xl font-bold text-content-primary flex items-center space-x-2">
          <Activity size={20} className="text-accent" />
          <span>Active Tasks</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          {runningJobs.length === 0 ? (
            <div className="col-span-full py-12 text-center bg-canvas rounded-xl border border-dashed border-border-default">
              <p className="text-content-tertiary text-sm italic">No active tasks at the moment.</p>
            </div>
          ) : (
            runningJobs.map(job => (
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
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-bold text-content-primary flex items-center space-x-2">
          <History size={20} className="text-content-tertiary" />
          <span>Recent Activity</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          {pastJobs.length === 0 && runningJobs.length === 0 ? (
            <div className="col-span-full py-12 text-center bg-canvas rounded-xl border border-dashed border-border-default">
              <p className="text-content-tertiary text-sm">No activity history yet.</p>
            </div>
          ) : (
            pastJobs.map(job => (
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
