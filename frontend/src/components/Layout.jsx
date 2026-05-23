import React from 'react';
import Sidebar from './Sidebar';

const Layout = ({ children, activeTab, setActiveTab }) => {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 shadow-sm z-10">
          <h2 className="text-xl font-semibold text-gray-800 capitalize">{activeTab}</h2>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500">Agent: Active</span>
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
