import React from 'react';
import { LayoutDashboard, Users, GitBranch, Settings } from 'lucide-react';

const Sidebar = ({ activeTab, setActiveTab }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { id: 'accounts', label: 'Accounts', icon: <Users size={20} /> },
    { id: 'pipelines', label: 'Pipelines', icon: <GitBranch size={20} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  return (
    <div className="w-64 bg-slate-900 text-white h-screen flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-blue-400">Story Autogen</h1>
      </div>
      <nav className="flex-1 mt-6">
        <ul className="space-y-2 px-4">
          {menuItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-slate-800 hover:text-white'
                }`}
              >
                {item.icon}
                <span className="font-medium">{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <div className="p-4 border-t border-slate-800 text-xs text-gray-500">
        v1.0.0-beta
      </div>
    </div>
  );
};

export default Sidebar;
