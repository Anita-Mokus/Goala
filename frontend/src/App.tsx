import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { apiClient } from './api/client';
import { siteAuthClient } from './api/siteAuth';
import SettingsPage from './pages/SettingsPage';
import HistoryPage from './pages/HistoryPage';
import LoginPage from './pages/LoginPage';
import MessengerPage from './pages/MessengerPage';

function App() {
  const [authStatus, setAuthStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const [siteStatus, backendStatus] = await Promise.all([
          siteAuthClient.getStatus(),
          apiClient.getBackendAuthStatus(),
        ]);
        setAuthStatus(siteStatus.authenticated && backendStatus.authenticated ? 'authenticated' : 'unauthenticated');
      } catch {
        setAuthStatus('unauthenticated');
      }
    };

    checkAuth();
  }, []);

  if (authStatus === 'loading') {
    return <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>Loading…</div>;
  }

  if (authStatus === 'unauthenticated') {
    return <LoginPage onAuthenticated={() => setAuthStatus('authenticated')} />;
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/settings" replace />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/messenger" element={<MessengerPage />} />
          <Route path="/login" element={<Navigate to="/settings" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
