import React, { useState } from 'react';
import Layout from './components/Layout';
import Accounts from './pages/Accounts';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <h3 className="text-lg font-bold mb-4">Welcome to Story Autogen</h3>
              <p className="text-gray-600">Start by configuring your accounts and then create a pipeline.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-blue-50 p-6 rounded-xl border border-blue-100">
                <p className="text-blue-800 font-bold text-2xl">0</p>
                <p className="text-blue-600 text-sm">Active Pipelines</p>
              </div>
              <div className="bg-green-50 p-6 rounded-xl border border-green-100">
                <p className="text-green-800 font-bold text-2xl">0</p>
                <p className="text-green-600 text-sm">Stories Published</p>
              </div>
              <div className="bg-purple-50 p-6 rounded-xl border border-purple-100">
                <p className="text-purple-800 font-bold text-2xl">0</p>
                <p className="text-purple-600 text-sm">Active Jobs</p>
              </div>
            </div>
          </div>
        );
      case 'accounts':
        return <Accounts />;
      case 'pipelines':
        return <div className="p-4 bg-white rounded-lg shadow">Pipeline Configuration (Coming Soon)</div>;
      case 'settings':
        return <div className="p-4 bg-white rounded-lg shadow">Global Settings (Coming Soon)</div>;
      default:
        return <div>Select a tab</div>;
    }
  };

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      {renderContent()}
    </Layout>
  );
}

export default App;
