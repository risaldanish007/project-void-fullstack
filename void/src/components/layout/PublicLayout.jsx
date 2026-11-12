import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";                                            
import Footer from "./Footer"; 

const PublicLayout = () => {
  return (
    <>
      <Navbar />
      {/* Container for the shop content */}
      <div className="w-full min-w-0 px-2 pt-4 sm:px-5 sm:pt-6 lg:px-8">
        <Outlet />

        <Footer />
      </div>
    </>
  );
};

export default PublicLayout;
