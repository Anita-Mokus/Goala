import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { apiClient, UserRole } from '../api/client';
import { siteAuthClient } from '../api/siteAuth';
import './Layout.css';

interface LayoutProps {
  children: ReactNode;
  role: UserRole;
}

const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrator',
  operator: 'Operator',
};

function Layout({ children, role }: LayoutProps) {
  const location = useLocation();

  const handleLogout = async () => {
    await Promise.all([
      siteAuthClient.logout().catch(() => undefined),
      apiClient.logoutBackend().catch(() => undefined),
    ]);
    window.location.href = '/login';
  };

  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="sidebar-header">
          <h1>Goala</h1>
          <p>Admin Panel</p>
          <p className="sidebar-role">{ROLE_LABELS[role]}</p>
        </div>
        <ul className="sidebar-menu">
          {role === 'admin' && (
            <li>
              <Link
                to="/settings"
                className={location.pathname === '/settings' ? 'active' : ''}
              >
                Settings
              </Link>
            </li>
          )}
          <li>
            <Link
              to="/history"
              className={location.pathname === '/history' ? 'active' : ''}
            >
              Chat History
            </Link>
          </li>
          <li>
            <Link
              to="/messenger"
              className={location.pathname === '/messenger' ? 'active' : ''}
            >
              Messenger Bot
            </Link>
          </li>
        </ul>
        <button type="button" className="sidebar-logout" onClick={handleLogout}>
          Log out
        </button>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}

export default Layout;
