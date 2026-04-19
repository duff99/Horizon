import { Outlet } from 'react-router-dom';

import { Sidebar } from '@/components/Sidebar';

export function Layout() {
  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden">
        <div className="mx-auto w-full max-w-[1320px] px-8 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
