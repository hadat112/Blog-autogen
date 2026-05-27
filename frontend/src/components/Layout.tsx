import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { Menu, Moon, Sun } from 'lucide-react';
import { Button } from './ui/Button';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const location = useLocation();

  // Extract the current path without the leading slash to use as the title
  const activeTab = location.pathname.substring(1) || 'dashboard';

  useEffect(() => {
    // Check local storage first, then system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
      setIsDarkMode(true);
      document.documentElement.classList.add('dark');
    } else {
      setIsDarkMode(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleTheme = () => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  return (
    <div className="flex h-screen bg-canvas overflow-hidden relative">
      <Sidebar
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        isCollapsed={isSidebarCollapsed}
        toggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      <div className="flex-1 flex flex-col overflow-hidden w-full transition-all duration-150">
        <header className="h-16 bg-surface border-b border-border-default flex items-center justify-between px-4 md:px-8 shadow-sm z-10 shrink-0">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 lg:hidden text-content-secondary hover:bg-surface-subtle rounded-lg transition-colors"
            >
              <Menu size={24} />
            </button>
            <h2 className="text-lg md:text-xl font-bold text-content-primary capitalize truncate">
              {activeTab}
            </h2>
          </div>

          <div className="flex items-center space-x-3 md:space-x-4 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="text-content-secondary hover:text-content-primary rounded-full"
              title="Toggle Theme"
            >
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </Button>
            
            <div className="hidden sm:flex items-center space-x-2">
              <span className="text-xs font-bold text-content-tertiary uppercase tracking-wider">Agent: Active</span>
              <div className="w-2.5 h-2.5 bg-status-success rounded-full animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
            </div>
            <div className="sm:hidden w-2.5 h-2.5 bg-status-success rounded-full animate-pulse"></div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <div className="max-w-7xl mx-auto w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
