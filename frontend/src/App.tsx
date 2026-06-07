import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { apiClient, UserRole } from './api/client';
import { siteAuthClient } from './api/siteAuth';
import SettingsPage from './pages/SettingsPage';
import HistoryPage from './pages/HistoryPage';
import LoginPage from './pages/LoginPage';
import MessengerPage from './pages/MessengerPage';

function getDefaultPath(role: UserRole): string {
  return role === 'admin' ? '/settings' : '/history';
}

function App() {
  const [authStatus, setAuthStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');
  const [role, setRole] = useState<UserRole | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const [siteStatus, backendStatus] = await Promise.all([
          siteAuthClient.getStatus(),
          apiClient.getBackendAuthStatus(),
        ]);

        if (siteStatus.authenticated && backendStatus.authenticated && backendStatus.role) {
          setRole(backendStatus.role);
          setAuthStatus('authenticated');
          return;
        }

        setRole(null);
        setAuthStatus('unauthenticated');
      } catch {
        setRole(null);
        setAuthStatus('unauthenticated');
      }
    };

    checkAuth();
  }, []);

  if (authStatus === 'loading') {
    return <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>Loading…</div>;
  }

  if (authStatus === 'unauthenticated' || !role) {
    return (
      <LoginPage
        onAuthenticated={(authenticatedRole) => {
          setRole(authenticatedRole);
          setAuthStatus('authenticated');
        }}
      />
    );
  }

  const defaultPath = getDefaultPath(role);

  return (
    <BrowserRouter>
      <Layout role={role}>
        <Routes>
          <Route path="/" element={<Navigate to={defaultPath} replace />} />
          <Route
            path="/settings"
            element={role === 'admin' ? <SettingsPage /> : <Navigate to="/history" replace />}
          />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/messenger" element={<MessengerPage />} />
          <Route path="/login" element={<Navigate to={defaultPath} replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
