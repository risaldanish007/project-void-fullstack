import { useSelector } from "react-redux";
import { Navigate, Outlet } from "react-router-dom";
import VoidLoader from "../../styles/VoidLoader";

const PublicRoute = () => {
  const { isAuthenticated, isInitializing } = useSelector(
    (state) => state.auth
  );

  if (isInitializing) {
    return <VoidLoader fullScreen label="Restoring session" />;
  }

  return isAuthenticated ? <Navigate to="/" replace /> : <Outlet />;
};

export default PublicRoute;
