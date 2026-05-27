import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { getAccounts } from '../api/client';

const PipelineForm = ({ pipeline, onClose, onSave }) => {
  const [accounts, setAccounts] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    type: 'story',
    language: 'uk',
    step_accounts: {
      ai: '',
      wp: '',
      fb: '',
      gs: '',
      tg: ''
    },
    schedule: '',
    is_active: true
  });

  useEffect(() => {
    const fetchAccounts = async () => {
      const { data } = await getAccounts();
      setAccounts(data);
    };
    fetchAccounts();

    if (pipeline) {
      setFormData(pipeline);
    }
  }, [pipeline]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleStepAccountChange = (step, accId) => {
    setFormData({
      ...formData,
      step_accounts: {
        ...formData.step_accounts,
        [step]: accId
      }
    });
  };

  const accountOptions = (type) => {
    return accounts
      .filter(a => a.type === type)
      .map(a => <option key={a.id} value={a.id}>{a.name}</option>);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden">
        <div className="flex justify-between items-center p-6 border-b border-gray-100">
          <h3 className="text-xl font-bold text-gray-900">
            {pipeline ? 'Edit Pipeline' : 'Create New Pipeline'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Pipeline Name</label>
              <input 
                type="text" 
                required
                className="w-full p-2 border border-gray-300 rounded-md"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Pipeline Type</label>
              <select 
                className="w-full p-2 border border-gray-300 rounded-md"
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              >
                <option value="story">Story Generation (AI)</option>
                <option value="crawl">Crawl Article (URL)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Language</label>
              <select 
                className="w-full p-2 border border-gray-300 rounded-md"
                value={formData.language}
                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
              >
                <option value="uk">Ukrainian</option>
                <option value="vi">Vietnamese</option>
                <option value="en">English</option>
                <option value="hr">Croatian</option>
                <option value="ro">Romanian</option>
                <option value="it">Italian</option>
                <option value="pl">Polish</option>
              </select>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="font-bold text-sm text-gray-400 uppercase tracking-wider">Step Configuration</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">AI Account (Text/Image)</label>
                <select 
                  className="w-full p-2 border border-gray-300 rounded-md"
                  value={formData.step_accounts.ai || ''}
                  onChange={(e) => handleStepAccountChange('ai', e.target.value)}
                >
                  <option value="">-- Select AI --</option>
                  {accounts.filter(a => a.type === 'ai').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">WordPress Account</label>
                <select 
                  className="w-full p-2 border border-gray-300 rounded-md"
                  value={formData.step_accounts.wp || ''}
                  onChange={(e) => handleStepAccountChange('wp', e.target.value)}
                >
                  <option value="">-- Select WP --</option>
                  {accounts.filter(a => a.type === 'wp').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Facebook Page</label>
                <select 
                  className="w-full p-2 border border-gray-300 rounded-md"
                  value={formData.step_accounts.fb || ''}
                  onChange={(e) => handleStepAccountChange('fb', e.target.value)}
                >
                  <option value="">-- Select FB --</option>
                  {accounts.filter(a => a.type === 'fb').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Google Sheets (Log)</label>
                <select 
                  className="w-full p-2 border border-gray-300 rounded-md"
                  value={formData.step_accounts.gs || ''}
                  onChange={(e) => handleStepAccountChange('gs', e.target.value)}
                >
                  <option value="">-- Select Sheets --</option>
                  {accounts.filter(a => a.type === 'gs').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Telegram (Notify)</label>
                <select 
                  className="w-full p-2 border border-gray-300 rounded-md"
                  value={formData.step_accounts.tg || ''}
                  onChange={(e) => handleStepAccountChange('tg', e.target.value)}
                >
                  <option value="">-- Select TG --</option>
                  {accounts.filter(a => a.type === 'tg').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="pt-6 flex justify-end space-x-3 border-t border-gray-100">
            <button 
              type="button" 
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium"
            >
              Cancel
            </button>
            <button 
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 transition shadow-sm"
            >
              {pipeline ? 'Update Pipeline' : 'Create Pipeline'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PipelineForm;
