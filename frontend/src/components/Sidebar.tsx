import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, GitBranch, Settings, X, Zap, ChevronLeft, ChevronRight, FlaskConical } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  isCollapsed?: boolean;
  toggleCollapse?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen, isCollapsed = false, toggleCollapse }) => {
  const menuItems = [
    { id: 'dashboard', path: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { id: 'accounts', path: '/accounts', label: 'Accounts', icon: <Users size={20} /> },
    { id: 'pipelines', path: '/pipelines', label: 'Pipelines', icon: <GitBranch size={20} /> },
    { id: 'translation-benchmarks', path: '/translation-benchmarks', label: 'Benchmarks', icon: <FlaskConical size={20} /> },
    { id: 'settings', path: '/settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  const handleTabClick = () => {
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

      <div className={`fixed inset-y-0 left-0 z-50 bg-surface border-r border-border-default text-content-primary transform transition-all duration-150 ease-in-out lg:relative lg:translate-x-0 ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } ${isCollapsed ? 'lg:w-20 w-64' : 'w-64'} flex flex-col shadow-2xl lg:shadow-none`}>
        <div className={`p-6 flex items-center h-20 ${isCollapsed ? 'lg:justify-center justify-between' : 'justify-between'}`}>
          <div className={`flex items-center overflow-hidden transition-all duration-150 ${isCollapsed ? 'lg:w-8 w-auto' : 'w-full'}`}>
            <div className="p-1.5 bg-accent/10 text-accent rounded-md shrink-0 flex items-center justify-center h-8 w-8">
               <Zap size={18} fill="currentColor" />
            </div>
            <h1 className={`ml-3 text-xl font-bold text-accent whitespace-nowrap transition-opacity duration-150 ${isCollapsed ? 'lg:opacity-0 lg:w-0' : 'opacity-100 w-auto'}`}>
              Story Autogen
            </h1>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 lg:hidden text-content-tertiary hover:text-content-primary shrink-0"
          >
            <X size={24} />
          </button>
        </div>

        <nav className="flex-1 mt-6 overflow-hidden">
          <ul className={`space-y-2 transition-all duration-150 ${isCollapsed ? 'lg:px-3 px-4' : 'px-4'}`}>
            {menuItems.map((item) => (
              <li key={item.id}>
                <NavLink
                  to={item.path}
                  onClick={handleTabClick}
                  title={item.label}
                  className={({ isActive }) =>
                    `w-full flex items-center ${isCollapsed ? 'lg:justify-center justify-start' : 'space-x-3'} p-3 rounded-lg transition-all ${
                      isActive
                        ? 'bg-[var(--button-primary-bg)] text-[var(--button-primary-text)] shadow-sm'
                        : 'text-content-secondary hover:bg-surface-subtle hover:text-content-primary'
                    }`
                  }
                >
                  <div className="shrink-0">{item.icon}</div>
                  <span className={`font-medium whitespace-nowrap transition-all duration-150 ${isCollapsed ? 'lg:w-0 lg:opacity-0 lg:ml-0 ml-3' : 'w-auto opacity-100 ml-3'}`}>
                    {item.label}
                  </span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className={`mt-auto p-4 border-t border-border-subtle flex items-center transition-all duration-150 ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
          <div className={`text-[10px] uppercase tracking-widest text-content-tertiary font-bold whitespace-nowrap overflow-hidden transition-all duration-150 ${isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'}`}>
            v1.0.0-beta
          </div>
          <button
            onClick={toggleCollapse}
            className="hidden lg:flex p-1.5 rounded-lg text-content-tertiary hover:bg-surface-subtle hover:text-content-primary transition-colors shrink-0"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
