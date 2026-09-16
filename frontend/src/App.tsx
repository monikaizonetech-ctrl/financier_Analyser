import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

import Landing from './pages/Landing';

import DashboardLayout from './layouts/DashboardLayout';
import Applicants from './pages/Applicants';
import NewApplication from './pages/NewApplication';
import Reports from './pages/Reports';
import Settings from './pages/Settings';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/applicants" element={<Applicants />} />
            <Route path="/applications/new" element={<NewApplication />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
