import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Accounts from './pages/Accounts';
import Pipelines from './pages/Pipelines';
import Dashboard from './pages/Dashboard';
import TranslationBenchmarks from './pages/TranslationBenchmarks';

const App: React.FC = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/pipelines" element={<Pipelines />} />
        <Route path="/translation-benchmarks" element={<TranslationBenchmarks />} />
        <Route path="/settings" element={<div className="p-4 bg-surface rounded-lg shadow border border-border-default">Global Settings (Coming Soon)</div>} />
        <Route path="*" element={<div>Page not found</div>} />
      </Routes>
    </Layout>
  );
}

export default App;
