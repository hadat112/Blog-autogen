import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Accounts from './pages/Accounts';
import Pipelines from './pages/Pipelines';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import RewriteArticle from './pages/RewriteArticle';
import GenerateStory from './pages/GenerateStory';
import PatternLibrary from './pages/PatternLibrary';
import WordPressPublisher from './pages/WordPressPublisher';

const App: React.FC = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/pipelines" element={<Pipelines />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/rewrite" element={<RewriteArticle />} />
        <Route path="/generate-story" element={<GenerateStory />} />
        <Route path="/pattern-library" element={<PatternLibrary />} />
        <Route path="/wordpress-publisher" element={<WordPressPublisher />} />
        <Route path="*" element={<div>Page not found</div>} />
      </Routes>
    </Layout>
  );
}

export default App;
