import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-[#090d16] text-slate-100 font-sans">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="flex flex-1 flex-col min-w-0">
        <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          <div className="mx-auto max-w-7xl">
            <div className="mb-5 flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-amber-100" role="alert">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" aria-hidden="true" />
              <p className="text-sm">
                <span className="font-semibold">Demo model active.</span>{' '}
                Predictions are not validated and must not be used to decide whether code is safe or to block merges.
              </p>
            </div>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
