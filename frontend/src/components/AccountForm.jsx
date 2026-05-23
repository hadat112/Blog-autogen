import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const AccountForm = ({ account, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    type: 'wp',
    config: {}
  });

  useEffect(() => {
    if (account) {
      setFormData(account);
    }
  }, [account]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleConfigChange = (key, value) => {
    setFormData({
      ...formData,
      config: {
        ...formData.config,
        [key]: value
      }
    });
  };

  const renderConfigFields = () => {
    switch (formData.type) {
      case 'wp':
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">WordPress URL</label>
              <input 
                type="url" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.url || ''}
                onChange={(e) => handleConfigChange('url', e.target.value)}
                placeholder="https://yourblog.com"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Username</label>
              <input 
                type="text" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.username || ''}
                onChange={(e) => handleConfigChange('username', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Application Password</label>
              <input 
                type="password" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.password || ''}
                onChange={(e) => handleConfigChange('password', e.target.value)}
              />
            </div>
          </>
        );
      case 'ai':
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">9router API Key</label>
              <input 
                type="password" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.api_key || ''}
                onChange={(e) => handleConfigChange('api_key', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Text Model</label>
              <input 
                type="text" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.text_model || 'gpt-4o'}
                onChange={(e) => handleConfigChange('text_model', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Image Model</label>
              <input 
                type="text" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.image_model || 'dall-e-3'}
                onChange={(e) => handleConfigChange('image_model', e.target.value)}
              />
            </div>
          </>
        );
      case 'fb':
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Page ID</label>
              <input 
                type="text" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.page_id || ''}
                onChange={(e) => handleConfigChange('page_id', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Access Token</label>
              <input 
                type="password" 
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.access_token || ''}
                onChange={(e) => handleConfigChange('access_token', e.target.value)}
              />
            </div>
          </>
        );
      default:
        return <p className="text-sm text-gray-500">Select an account type to configure</p>;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="flex justify-between items-center p-6 border-b border-gray-100">
          <h3 className="text-xl font-bold text-gray-900">
            {account ? 'Edit Account' : 'Add New Account'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">
            <X size={24} />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700">Account Name</label>
            <input 
              type="text" 
              required
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. My WordPress Blog"
            />
          </div>
          
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700">Service Type</label>
            <select 
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value, config: {} })}
            >
              <option value="wp">WordPress</option>
              <option value="fb">Facebook Page</option>
              <option value="ai">AI (9router)</option>
              <option value="gs">Google Sheets</option>
              <option value="tg">Telegram</option>
            </select>
          </div>

          <div className="pt-4 border-t border-gray-50 space-y-4">
            {renderConfigFields()}
          </div>

          <div className="pt-6 flex justify-end space-x-3">
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
              {account ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AccountForm;
