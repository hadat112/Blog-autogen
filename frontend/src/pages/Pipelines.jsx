import React, { useState, useEffect } from 'react';
import { getPipelines, deletePipeline, createPipeline, updatePipeline } from '../api/client';
import { Plus, Trash2, Edit2, Play, GitBranch } from 'lucide-react';
import PipelineForm from '../components/PipelineForm';

const Pipelines = () => {
  const [pipelines, setPipelines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingPipeline, setEditingPipeline] = useState(null);

  const fetchPipelines = async () => {
    try {
      const { data } = await getPipelines();
      setPipelines(data);
    } catch (error) {
      console.error('Failed to fetch pipelines', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelines();
  }, []);

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this pipeline?')) {
      try {
        await deletePipeline(id);
        setPipelines(pipelines.filter(p => p.id !== id));
      } catch (error) {
        alert('Failed to delete pipeline');
      }
    }
  };

  const handleSavePipeline = async (formData) => {
    try {
      if (editingPipeline) {
        await updatePipeline(editingPipeline.id, formData);
      } else {
        await createPipeline(formData);
      }
      setShowForm(false);
      setEditingPipeline(null);
      fetchPipelines();
    } catch (error) {
      alert('Failed to save pipeline: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) return <div className="text-center py-10">Loading pipelines...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-bold text-gray-800">Process Pipelines</h3>
        <button 
          onClick={() => { setEditingPipeline(null); setShowForm(true); }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 hover:bg-blue-700 transition shadow-sm"
        >
          <Plus size={18} />
          <span>New Pipeline</span>
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {pipelines.length === 0 ? (
          <div className="py-20 text-center bg-white rounded-xl border border-dashed border-gray-300">
            <p className="text-gray-500">No pipelines defined. Create one to start processing stories.</p>
          </div>
        ) : (
          pipelines.map((p) => (
            <div key={p.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between hover:shadow-md transition-shadow">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
                  <GitBranch size={24} />
                </div>
                <div>
                  <h4 className="font-bold text-gray-900">{p.name}</h4>
                  <div className="flex items-center space-x-3 mt-1">
                    <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-2 py-0.5 rounded uppercase">
                      {p.language}
                    </span>
                    <span className="text-xs text-gray-400">
                      Steps: {Object.values(p.step_accounts).filter(v => v).length} configured
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button 
                  onClick={() => { setEditingPipeline(p); setShowForm(true); }}
                  className="p-2 text-gray-400 hover:text-amber-600 transition-colors"
                >
                  <Edit2 size={18} />
                </button>
                <button 
                  onClick={() => handleDelete(p.id)}
                  className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {showForm && (
        <PipelineForm 
          pipeline={editingPipeline} 
          onClose={() => { setShowForm(false); setEditingPipeline(null); }}
          onSave={handleSavePipeline}
        />
      )}
    </div>
  );
};

export default Pipelines;
