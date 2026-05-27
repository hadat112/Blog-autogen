import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJobs } from '../../api/client';
import QuickRun from './components/QuickRun';
import JobCard from './components/JobCard';
import JobDetailsModal from './components/JobDetailsModal';
import DashboardSkeleton from './components/DashboardSkeleton';
import { History, Activity } from 'lucide-react';
import { Job } from '../../api/types';

const Dashboard = () => {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const { data: jobs = [], isLoading, refetch } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const { data } = await getJobs();
      return data;
    },
    refetchInterval: 3000, // Poll every 3 seconds
  });

  const runningJobs = jobs.filter(j => j.status === 'running');
  const pastJobs = jobs.filter(j => j.status !== 'running').slice(0, 10);
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
              <JobCard key={job.id} job={job as any} onClick={() => setSelectedJobId(job.id)} />
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
              <JobCard key={job.id} job={job as any} onClick={() => setSelectedJobId(job.id)} />
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
