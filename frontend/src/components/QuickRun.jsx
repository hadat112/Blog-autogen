import React, { useState, useEffect } from 'react';
import { Play, Send } from 'lucide-react';
import { getPipelines, runPipeline } from '../api/client';

const QuickRun = ({ onRunStarted }) => {
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState('');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchPipelines = async () => {
      const { data } = await getPipelines();
      setPipelines(data);
      if (data.length > 0) setSelectedPipeline(data[0].id);
    };
    fetchPipelines();
  }, []);

  const handleRun = async (e) => {
    e.preventDefault();
    if (!selectedPipeline || !input.trim()) return;

    setLoading(true);
    try {
      const { data } = await runPipeline(selectedPipeline, { prompt: input.trim() });
      setInput('');
      if (onRunStarted) onRunStarted(data.job_id);
    } catch (error) {
      alert('Failed to start pipeline: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
      <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center space-x-2">
        <Play size={18} className="text-green-600" />
        <span>Quick Run</span>
      </h3>
      
      <form onSubmit={handleRun} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-1">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1 block">Pipeline</label>
            <select 
              className="w-full p-2 border border-gray-300 rounded-md bg-gray-50 focus:bg-white transition-colors"
              value={selectedPipeline}
              onChange={(e) => setSelectedPipeline(e.target.value)}
            >
              {pipelines.map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.language})</option>
              ))}
              {pipelines.length === 0 && <option value="">No pipelines found</option>}
            </select>
          </div>
          
          <div className="md:col-span-2">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1 block">URL or Prompt</label>
            <div className="relative">
              <input 
                type="text" 
                className="w-full p-2 pr-12 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                placeholder="Paste an article URL or enter a prompt..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <button 
                type="submit"
                disabled={loading || !input.trim() || !selectedPipeline}
                className="absolute right-1 top-1 bottom-1 px-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 transition-colors"
              >
                {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <Send size={16} />}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default QuickRun;
