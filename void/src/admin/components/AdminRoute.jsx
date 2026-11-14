import { useSelector } from 'react-redux';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import NotFound from '../../pages/NotFound';
import VoidLoader from '../../styles/VoidLoader';

const AdminRoute = () => {
  const { user, isAuthenticated, isInitializing } = useSelector(
    (state) => state.auth
  );
  const location = useLocation();

  if (isInitializing) {
    return <VoidLoader fullScreen label="Restoring session" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Authenticated non-admin accounts do not receive access to admin routes.
  if (user?.role !== 'admin') {
    return <NotFound/>;
  }

  return <Outlet />;
};

export default AdminRoute;
