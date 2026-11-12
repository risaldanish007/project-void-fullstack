import { useSelector } from "react-redux";
import { Navigate, Outlet } from "react-router-dom";

const PublicRoute = () => {
  const { isAuthenticated, isInitializing } = useSelector(
    (state) => state.auth
  );

  if (isInitializing) {
    return <div>Restoring session...</div>;
  }

  return isAuthenticated ? <Navigate to="/" replace /> : <Outlet />;
};

export default PublicRoute;
