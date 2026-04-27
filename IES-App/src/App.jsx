import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import FilingHistory from './pages/FilingHistory';
import FilingDetail from './pages/FilingDetail';
import Settings from './pages/Settings';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"           element={<Dashboard />} />
        <Route path="/history"    element={<FilingHistory />} />
        <Route path="/filing/:id" element={<FilingDetail />} />
        <Route path="/settings"   element={<Settings />} />
        <Route path="*"           element={<Dashboard />} />
      </Routes>
    </Layout>
  );
}
