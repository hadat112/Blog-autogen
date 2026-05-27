import React from 'react';
import { LayoutDashboard, Users, GitBranch, Settings, X } from 'lucide-react';

const Sidebar = ({ activeTab, setActiveTab, isOpen, setIsOpen }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { id: 'accounts', label: 'Accounts', icon: <Users size={20} /> },
    { id: 'pipelines', label: 'Pipelines', icon: <GitBranch size={20} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  const handleTabClick = (id) => {
    setActiveTab(id);
    if (window.innerWidth < 1024) {
      setIsOpen(false);
    }
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 text-white transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } flex flex-col shadow-2xl lg:shadow-none`}>
        <div className="p-6 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-blue-400">Story Autogen</h1>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 lg:hidden text-gray-400 hover:text-white"
          >
            <X size={24} />
          </button>
        </div>

        <nav className="flex-1 mt-6">
          <ul className="space-y-2 px-4">
            {menuItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => handleTabClick(item.id)}
                  className={`w-full flex items-center space-x-3 p-3 rounded-lg transition-all ${
                    activeTab === item.id
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
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

        <div className="p-4 border-t border-slate-800 text-[10px] uppercase tracking-widest text-gray-500 font-bold">
          v1.0.0-beta
        </div>
      </div>
    </>
  );
};

export default Sidebar;
