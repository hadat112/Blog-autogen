import React, { useState } from 'react';
import Layout from './components/Layout';
import Accounts from './pages/Accounts';
import Pipelines from './pages/Pipelines';
import Dashboard from './pages/Dashboard';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'accounts':
        return <Accounts />;
      case 'pipelines':
        return <Pipelines />;
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
