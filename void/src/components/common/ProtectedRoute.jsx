import { useSelector } from "react-redux";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import VoidLoader from "../../styles/VoidLoader";

const ProtectedRoute = ({ adminOnly = false }) => {
  const { isAuthenticated, isInitializing, user } = useSelector(
    (state) => state.auth
  );
  const location = useLocation();

  if (isInitializing) {
    return <VoidLoader fullScreen label="Restoring session" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && user?.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
