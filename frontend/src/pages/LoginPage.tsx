import { useState } from 'react';
import { apiClient } from '../api/client';
import { siteAuthClient } from '../api/siteAuth';
import './LoginPage.css';

interface LoginPageProps {
  onAuthenticated: () => void;
}

function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await siteAuthClient.login(token);

      try {
        await apiClient.loginBackend(token);
      } catch (backendError) {
        await siteAuthClient.logout().catch(() => undefined);
        throw backendError;
      }

      setToken('');
      onAuthenticated();
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-backdrop" />
      <div className="login-card">
        <div className="login-badge">Protected access</div>
        <h1>Goala Admin Panel</h1>
        <p>
          Enter the private access token to unlock the dashboard, backend API, and live Messenger control.
        </p>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="access-token">Access token</label>
          <input
            id="access-token"
            name="access-token"
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Paste your private token"
            autoComplete="one-time-code"
            required
          />

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Unlocking…' : 'Unlock dashboard'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;