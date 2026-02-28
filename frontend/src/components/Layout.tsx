import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

interface LayoutProps {
  children: ReactNode;
}

function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="sidebar-header">
          <h1>Goala</h1>
          <p>Admin Panel</p>
        </div>
        <ul className="sidebar-menu">
          <li>
            <Link
              to="/settings"
              className={location.pathname === '/settings' ? 'active' : ''}
            >
              Settings
            </Link>
          </li>
          <li>
            <Link
              to="/history"
              className={location.pathname === '/history' ? 'active' : ''}
            >
              Chat History
            </Link>
          </li>
        </ul>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}

export default Layout;
