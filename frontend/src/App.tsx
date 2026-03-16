import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import SettingsPage from './pages/SettingsPage';
import HistoryPage from './pages/HistoryPage';
import MessengerPage from './pages/MessengerPage';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/settings" replace />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/messenger" element={<MessengerPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
