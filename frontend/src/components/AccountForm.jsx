import React, { useState, useEffect } from 'react';
import { X, RefreshCw, CheckCircle, XCircle, Search } from 'lucide-react';
import { testAccount, getWPCategories } from '../api/client';

const AccountForm = ({ account, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    type: 'wp',
    config: {}
  });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [categories, setCategories] = useState([]);
  const [fetchingCats, setFetchingCats] = useState(false);

  useEffect(() => {
    if (account) {
      setFormData(account);
    }
  }, [account]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Send only type and config for testing via unified API
      const testData = {
        type: formData.type,
        config: formData.config
      };
      await testAccount(testData);
      setTestResult({ success: true, message: 'Connection verified successfully!' });
    } catch (error) {
      setTestResult({ success: false, message: error.response?.data?.detail || 'Connection test failed.' });
    } finally {
      setTesting(false);
    }
  };

  const handleFetchCategories = async () => {
    if (!formData.config.url) return;
    setFetchingCats(true);
    try {
      const { data } = await getWPCategories(formData.config);
      setCategories(data);
    } catch (error) {
      alert('Failed to fetch categories: ' + (error.response?.data?.detail || error.message));
    } finally {
      setFetchingCats(false);
    }
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
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Default Category</label>
              <div className="flex space-x-2">
                {categories.length > 0 ? (
                  <select
                    className="flex-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    value={formData.config.category_id || ''}
                    onChange={(e) => handleConfigChange('category_id', e.target.value)}
                  >
                    <option value="">-- Use Default --</option>
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.name} ({cat.count})</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    className="flex-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    value={formData.config.category_id || ''}
                    onChange={(e) => handleConfigChange('category_id', e.target.value)}
                    placeholder="e.g. 1"
                  />
                )}
                <button
                  type="button"
                  onClick={handleFetchCategories}
                  disabled={fetchingCats || !formData.config.url}
                  className="px-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md border border-gray-300 flex items-center transition"
                  title="Fetch Categories from site"
                >
                  {fetchingCats ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
                </button>
              </div>
              <p className="text-[10px] text-gray-400 italic">
                {categories.length > 0 ? "Select from list or click search to refresh" : "Enter ID or click search to fetch list from site"}
              </p>
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
              <label className="text-sm font-medium text-gray-700">Base URL</label>
              <input
                type="url"
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.base_url || 'http://localhost:20128/v1'}
                onChange={(e) => handleConfigChange('base_url', e.target.value)}
                placeholder="http://localhost:20128/v1"
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
      case 'gs':
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Spreadsheet ID</label>
              <input
                type="text"
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.spreadsheet_id || ''}
                onChange={(e) => handleConfigChange('spreadsheet_id', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Credentials JSON Path</label>
              <input
                type="text"
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.credentials_path || 'credentials.json'}
                onChange={(e) => handleConfigChange('credentials_path', e.target.value)}
              />
            </div>
          </>
        );
      case 'tg':
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Bot Token</label>
              <input
                type="password"
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.bot_token || ''}
                onChange={(e) => handleConfigChange('bot_token', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Chat ID</label>
              <input
                type="text"
                required
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                value={formData.config.chat_id || ''}
                onChange={(e) => handleConfigChange('chat_id', e.target.value)}
              />
            </div>
          </>
        );
      default:
        return <p className="text-sm text-gray-500">Select an account type to configure</p>;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
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

          <div className="pt-6 flex flex-col space-y-3">
            {testResult && (
              <div className={`p-3 rounded-lg text-sm flex items-start space-x-2 ${
                testResult.success ? 'bg-green-50 text-green-700 border border-green-100' : 'bg-red-50 text-red-700 border border-red-100'
              }`}>
                {testResult.success ? <CheckCircle size={18} className="mt-0.5" /> : <XCircle size={18} className="mt-0.5" />}
                <span>{testResult.message}</span>
              </div>
            )}

            <div className="flex justify-between items-center space-x-3 pt-2">
              <button
                type="button"
                onClick={handleTest}
                disabled={testing}
                className="flex items-center space-x-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-md font-medium transition disabled:opacity-50"
              >
                <RefreshCw size={18} className={testing ? 'animate-spin' : ''} />
                <span>Test Connection</span>
              </button>

              <div className="flex space-x-3">
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
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AccountForm;
