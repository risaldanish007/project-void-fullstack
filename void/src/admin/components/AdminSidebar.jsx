import { NavLink } from 'react-router-dom';

const AdminSidebar = () => {
  const links = [
    { name: 'Dashboard', path: '/admin', icon: '⌬' },
    { name: 'Inventory', path: '/admin/inventory', icon: '⧉' },
    { name: 'orders', path: '/admin/orders', icon: '▨' }, // New Sector
    { name: 'Users', path: '/admin/users', icon: '⚇' },  // New Sector
  ];

  return (
    <aside className="w-full md:w-64 bg-[#0a0a0a] border-b md:border-b-0 md:border-r border-white/5 fixed md:inset-y-0 md:left-0 top-0 left-0 flex flex-row md:flex-col items-center md:items-stretch justify-between md:justify-start px-2 sm:px-4 py-2.5 md:p-8 z-50 min-w-0">
      {/* Branding Node */}
      <div className="hidden md:block md:mb-16">
        <h2 className="text-lg md:text-2xl font-black italic tracking-tighter text-white">
          VOID<span className="text-green-500">CORP</span>
        </h2>
        <div className="hidden md:flex items-center gap-2 mt-1">
          <div className="w-1 h-1 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-[8px] font-mono text-white/20 uppercase tracking-[0.5em]">
            Architect_v.2.0
          </span>
        </div>
      </div>

      {/* Navigation Uplinks */}
      <nav className="flex flex-1 min-w-0 md:flex-initial justify-start md:justify-start items-center md:items-stretch gap-1 md:gap-0 md:flex-col md:space-y-2 overflow-x-auto scrollbar-hide">
        {links.map((link) => (
          <NavLink
            key={link.name}
            to={link.path}
            end={link.path === '/admin'}
            className={({ isActive }) => `
              flex shrink-0 items-center gap-1 md:gap-4 px-2 sm:px-2.5 md:px-5 py-2.5 md:py-3 rounded-xl transition-all font-mono text-[8px] sm:text-[9px] md:text-[10px] uppercase tracking-wider md:tracking-[0.3em]
              ${isActive
                ? 'bg-white text-black font-bold shadow-[0_0_20px_rgba(255,255,255,0.1)]'
                : 'text-gray-500 hover:text-white hover:bg-white/5'}
            `}
          >
            <span className="text-[14px] leading-none">{link.icon}</span>
            {link.name}
          </NavLink>
        ))}
      </nav>

      {/* Shutdown Protocol */}
      <div className="shrink-0 md:mt-auto md:pt-8 md:border-t border-white/5 pl-1">
        <NavLink
          to="/"
          className="group flex items-center gap-1 md:gap-2 text-white/50 md:text-white/20 hover:text-green-500 font-mono text-[7px] sm:text-[8px] md:text-[9px] tracking-wide md:tracking-widest uppercase transition-colors whitespace-nowrap"
        >
          <span className="group-hover:-translate-x-1 transition-transform">←</span>
          Exit_Console
        </NavLink>
      </div>
    </aside>
  );
};

export default AdminSidebar;