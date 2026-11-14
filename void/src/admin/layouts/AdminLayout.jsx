import { Outlet } from 'react-router-dom';
import AdminSidebar from '../components/AdminSidebar';
import { useAppStartup } from '../../components/common/AppStartupContext';

const AdminLayout = () => {
  const appIsStarting = useAppStartup();

  return (
    <div className="min-h-screen bg-[#050505] text-white flex flex-col md:flex-row">
      {!appIsStarting && <AdminSidebar />}
      <main className="flex-1 min-w-0 md:ml-64 p-3 pt-20 sm:p-6 sm:pt-24 lg:p-12">
        {!appIsStarting && (
          <header className="mb-8 sm:mb-12 border-b border-white/5 pb-6 sm:pb-8 flex justify-between items-end">
            <div>
              <span className="text-green-500 font-mono text-[9px] tracking-[0.6em] uppercase animate-pulse">System_Active</span>
              <h1 className="text-3xl sm:text-4xl font-black uppercase italic tracking-tighter mt-2 text-white">
                ADMIN <span className="text-white/10 font-thin not-italic">panel</span>
              </h1>
            </div>
          </header>
        )}
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;
