import { Outlet } from 'react-router-dom';
import AdminSidebar from '../components/AdminSidebar';
import { useAppStartup } from '../../components/common/AppStartupContext';
import '../admin.css';

const AdminLayout = () => {
  const appIsStarting = useAppStartup();

  return (
    <div className="admin-shell min-h-screen bg-[#070807] text-white flex flex-col md:flex-row">
      {!appIsStarting && <AdminSidebar />}
      <main className="admin-main flex-1 min-w-0 md:ml-64 p-3 pt-20 sm:p-6 sm:pt-24 lg:p-10">
        {!appIsStarting && (
          <header className="admin-brand-header mb-7 border-b border-white/10 pb-5 flex justify-between items-end">
            <div>
              <span className="text-green-400 font-mono text-[10px] tracking-[0.24em] uppercase">VOID / OPERATIONS</span>
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mt-2 text-white">
                Admin <span className="text-white/40 font-normal">console</span>
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
