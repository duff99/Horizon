import { Outlet } from 'react-router-dom';

import { Sidebar } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

export function Layout() {
  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-x-hidden">
          <div className="mx-auto w-full max-w-[1320px] px-8 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
