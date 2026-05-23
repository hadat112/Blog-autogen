import React, { useState, useEffect } from 'react';
import { getAccounts, deleteAccount, testAccount, createAccount, updateAccount } from '../api/client';
import { Plus, Trash2, RefreshCw, CheckCircle, XCircle, Edit2 } from 'lucide-react';
import AccountForm from '../components/AccountForm';

const Accounts = () => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testingId, setTestingId] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [showForm, setShowForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);

  const fetchAccounts = async () => {
    try {
      const { data } = await getAccounts();
      setAccounts(data);
    } catch (error) {
      console.error('Failed to fetch accounts', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this account?')) {
      try {
        await deleteAccount(id);
        setAccounts(accounts.filter(a => a.id !== id));
      } catch (error) {
        alert('Failed to delete account');
      }
    }
  };

  const handleTest = async (id) => {
    setTestingId(id);
    try {
      await testAccount(id);
      setTestResults({ ...testResults, [id]: { success: true } });
    } catch (error) {
      setTestResults({ ...testResults, [id]: { success: false, message: error.response?.data?.detail || 'Test failed' } });
    } finally {
      setTestingId(null);
    }
  };

  const handleSaveAccount = async (formData) => {
    try {
      if (editingAccount) {
        await updateAccount(editingAccount.id, formData);
      } else {
        await createAccount(formData);
      }
      setShowForm(false);
      setEditingAccount(null);
      fetchAccounts();
    } catch (error) {
      alert('Failed to save account: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) return <div className="text-center py-10">Loading accounts...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-bold text-gray-800">Service Accounts</h3>
        <button 
          onClick={() => { setEditingAccount(null); setShowForm(true); }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 hover:bg-blue-700 transition shadow-sm"
        >
          <Plus size={18} />
          <span>Add Account</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {accounts.length === 0 ? (
          <div className="col-span-full py-20 text-center bg-white rounded-xl border border-dashed border-gray-300">
            <p className="text-gray-500">No accounts configured yet.</p>
          </div>
        ) : (
          accounts.map((acc) => (
            <div key={acc.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow group">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h4 className="font-bold text-gray-900 group-hover:text-blue-600 transition-colors">{acc.name}</h4>
                  <span className="text-[10px] uppercase font-bold tracking-widest text-gray-400 bg-gray-50 px-2 py-0.5 rounded border border-gray-100">
                    {acc.type}
                  </span>
                </div>
                <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => handleTest(acc.id)}
                    disabled={testingId === acc.id}
                    title="Test Connection"
                    className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                  >
                    <RefreshCw size={16} className={testingId === acc.id ? 'animate-spin' : ''} />
                  </button>
                  <button 
                    onClick={() => { setEditingAccount(acc); setShowForm(true); }}
                    title="Edit Account"
                    className="p-2 text-gray-400 hover:text-amber-600 transition-colors"
                  >
                    <Edit2 size={16} />
                  </button>
                  <button 
                    onClick={() => handleDelete(acc.id)}
                    title="Delete Account"
                    className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              <div className="text-xs text-gray-500 space-y-1 mb-4 font-mono truncate">
                {acc.type === 'wp' && <p>URL: {acc.config.url}</p>}
                {acc.type === 'ai' && <p>Model: {acc.config.text_model}</p>}
                {acc.type === 'fb' && <p>Page: {acc.config.page_id}</p>}
              </div>

              {testResults[acc.id] && (
                <div className={`flex items-center space-x-2 text-[11px] font-semibold p-2 rounded-lg ${
                  testResults[acc.id].success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                }`}>
                  {testResults[acc.id].success ? (
                    <><CheckCircle size={14} /> <span>Verified</span></>
                  ) : (
                    <><XCircle size={14} /> <span className="truncate">{testResults[acc.id].message}</span></>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showForm && (
        <AccountForm 
          account={editingAccount} 
          onClose={() => { setShowForm(false); setEditingAccount(null); }}
          onSave={handleSaveAccount}
        />
      )}
    </div>
  );
};

export default Accounts;
