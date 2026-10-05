import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";
import DashboardLayout from "./layouts/DashboardLayout.jsx";

import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import MyReports from "./pages/MyReports.jsx";
import TeamReports from "./pages/TeamReports.jsx";
import TeamManagement from "./pages/TeamManagement.jsx";
import Billing from "./pages/Billing.jsx";
import Help from "./pages/Help.jsx";
import UploadReport from "./pages/UploadReport.jsx";
import ContactUs from "./pages/ContactUs.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Full-screen upload workflow (no sidebar), still auth-protected */}
      <Route element={<ProtectedRoute />}>
        <Route path="/upload-report/:reportId" element={<UploadReport />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/my-reports" element={<MyReports />} />
          <Route path="/team-reports" element={<TeamReports />} />
          <Route path="/billing" element={<Billing />} />
          <Route path="/help" element={<Help />} />
          <Route path="/contact-us" element={<ContactUs />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={["Admin", "Manager"]} />}>
        <Route element={<DashboardLayout />}>
          <Route path="/team-management" element={<TeamManagement />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
