import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import Header from "../components/Header.jsx";

export default function DashboardLayout() {
  return (
    <div className="flex min-h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
