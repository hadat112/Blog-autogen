import React, { useState, useEffect } from 'react';
import { getJobs } from '../api/client';
import QuickRun from '../components/QuickRun';
import JobCard from '../components/JobCard';
import JobDetailsModal from '../components/JobDetailsModal';
import { History, Activity } from 'lucide-react';

const Dashboard = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJobId, setSelectedJobId] = useState(null);

  const fetchJobs = async () => {
    try {
      const { data } = await getJobs();
      setJobs(data);
    } catch (error) {
      console.error('Failed to fetch jobs', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const runningJobs = jobs.filter(j => j.status === 'running');
  const pastJobs = jobs.filter(j => j.status !== 'running').slice(0, 10);
  const selectedJob = jobs.find(j => j.id === selectedJobId);

  return (
    <div className="space-y-8">
      <QuickRun onRunStarted={fetchJobs} />

      <div className="space-y-4">
        <h3 className="text-xl font-bold text-gray-800 flex items-center space-x-2">
          <Activity size={20} className="text-blue-600" />
          <span>Active Tasks</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          {runningJobs.length === 0 ? (
            <div className="col-span-full py-12 text-center bg-gray-50 rounded-xl border border-dashed border-gray-200">
              <p className="text-gray-400 text-sm italic">No active tasks at the moment.</p>
            </div>
          ) : (
            runningJobs.map(job => (
              <JobCard key={job.id} job={job} onClick={() => setSelectedJobId(job.id)} />
            ))
          )}
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-bold text-gray-800 flex items-center space-x-2">
          <History size={20} className="text-gray-400" />
          <span>Recent Activity</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          {pastJobs.length === 0 && runningJobs.length === 0 && !loading ? (
            <div className="col-span-full py-12 text-center bg-gray-50 rounded-xl border border-dashed border-gray-200">
              <p className="text-gray-400 text-sm">No activity history yet.</p>
            </div>
          ) : (
            pastJobs.map(job => (
              <JobCard key={job.id} job={job} onClick={() => setSelectedJobId(job.id)} />
            ))
          )}
        </div>
      </div>

      {selectedJob && (
        <JobDetailsModal 
          job={selectedJob} 
          onClose={() => setSelectedJobId(null)} 
        />
      )}
    </div>
  );
};

export default Dashboard;
