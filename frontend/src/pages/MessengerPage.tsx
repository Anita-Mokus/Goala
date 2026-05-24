import React, { useState, useEffect } from 'react';
import { apiClient, MessengerStatus } from '../api/client';
import VncViewer from '../components/VncViewer';
import './MessengerPage.css';

function resolveVncWsUrl(): string | undefined {
  const configuredBaseUrl = import.meta.env.VITE_NOVNC_URL?.trim();

  if (!configuredBaseUrl) {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${window.location.host}/websockify`;
  }

  if (/^wss?:\/\//i.test(configuredBaseUrl)) {
    return configuredBaseUrl.replace(/\/$/, '');
  }

  const absoluteBaseUrl = /^https?:\/\//i.test(configuredBaseUrl)
    ? configuredBaseUrl
    : `https://${configuredBaseUrl}`;
  const parsedUrl = new URL(absoluteBaseUrl);
  const websocketBaseUrl = `${parsedUrl.protocol === 'https:' ? 'wss:' : 'ws:'}//${parsedUrl.host}`;
  const explicitPath = parsedUrl.pathname && parsedUrl.pathname !== '/'
    ? parsedUrl.pathname.replace(/\/$/, '')
    : '';

  return `${websocketBaseUrl}${explicitPath}`;
}

const MessengerPage: React.FC = () => {
  const [status, setStatus] = useState<MessengerStatus>({
    running: false,
    paused: false,
    message_count: 0,
    last_message_timestamp: null,
    uptime_seconds: 0,
    config_valid: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await apiClient.getMessengerStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await apiClient.startMessenger();
      setSuccess(response.message);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start bot');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await apiClient.stopMessenger();
      setSuccess(response.message);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop bot');
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await apiClient.pauseMessenger();
      setSuccess(response.message);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause bot');
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await apiClient.resumeMessenger();
      setSuccess(response.message);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume bot');
    } finally {
      setLoading(false);
    }
  };

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const formatTimestamp = (timestamp: string | null): string => {
    if (!timestamp) return 'Never';
    return new Date(timestamp).toLocaleString();
  };

  const vncWsUrl = resolveVncWsUrl();

  return (
    <div className="messenger-page">
      <div className="messenger-header">
        <h1>Messenger Bot Control</h1>
        <p className="subtitle">Monitor and control the Facebook Messenger automation bot</p>
      </div>

      {error && (
        <div className="alert alert-error">
          <svg className="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          <svg className="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{success}</span>
        </div>
      )}

      {!status.config_valid && !status.running && (
        <div className="alert alert-warning">
          <svg className="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Configuration is invalid. Please check MESSENGER_CHROME_PROFILE_PATH in .env file.</span>
        </div>
      )}

      <div className="status-grid">
        <div className="status-card">
          <div className="status-card-header">
            <h3>Bot Status</h3>
            <span className={`status-badge ${status.running ? 'status-running' : 'status-stopped'}`}>
              {status.running ? (status.paused ? 'Paused' : 'Running') : 'Stopped'}
            </span>
          </div>
          <div className="status-details">
            <div className="status-item">
              <span className="status-label">Messages Processed:</span>
              <span className="status-value">{status.message_count}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Uptime:</span>
              <span className="status-value">{formatUptime(status.uptime_seconds)}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Last Message:</span>
              <span className="status-value">{formatTimestamp(status.last_message_timestamp)}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Configuration:</span>
              <span className={`status-value ${status.config_valid ? 'text-success' : 'text-error'}`}>
                {status.config_valid ? 'Valid' : 'Invalid'}
              </span>
            </div>
          </div>
        </div>

        <div className="control-card">
          <h3>Bot Controls</h3>
          <div className="control-buttons">
            {!status.running ? (
              <button
                className="btn btn-primary btn-large"
                onClick={handleStart}
                disabled={loading || !status.config_valid}
              >
                {loading ? 'Starting...' : 'Start Bot'}
              </button>
            ) : (
              <>
                {status.paused ? (
                  <button
                    className="btn btn-success btn-large"
                    onClick={handleResume}
                    disabled={loading}
                  >
                    {loading ? 'Resuming...' : 'Resume Bot'}
                  </button>
                ) : (
                  <button
                    className="btn btn-warning btn-large"
                    onClick={handlePause}
                    disabled={loading}
                  >
                    {loading ? 'Pausing...' : 'Pause Bot'}
                  </button>
                )}
                <button
                  className="btn btn-danger btn-large"
                  onClick={handleStop}
                  disabled={loading}
                >
                  {loading ? 'Stopping...' : 'Stop Bot'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="info-section">
        <h3>Chrome Browser — Live View</h3>
        <VncViewer connected={status.running} wsUrl={vncWsUrl} />
      </div>

      <div className="info-section">
        <h3>Setup Instructions</h3>
        <div className="info-card">
          <div className="info-step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h4>Start the Bot</h4>
              <p>Click the "Start Bot" button above. Chrome will launch inside Docker and open Messenger automatically. You'll see it appear in the live view above.</p>
            </div>
          </div>

          <div className="info-step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h4>Log in to Messenger</h4>
              <p>Use the live Chrome view above to log in with your Facebook account. Check "Stay logged in" so the session persists across restarts.</p>
            </div>
          </div>

          <div className="info-step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h4>Let the Bot Work</h4>
              <p>Once logged in, the bot will automatically monitor your Messenger inbox and respond using the Goala RAG system. You can watch it work in real-time in the viewer above!</p>
            </div>
          </div>
        </div>
      </div>

      <div className="info-section">
        <h3>How It Works</h3>
        <div className="how-it-works">
          <div className="work-item">
            <div className="work-icon">📱</div>
            <div className="work-content">
              <h4>Monitors Messages</h4>
              <p>The bot continuously checks for unread messages in your Messenger inbox every 10-15 seconds.</p>
            </div>
          </div>
          <div className="work-item">
            <div className="work-icon">🤖</div>
            <div className="work-content">
              <h4>Processes with AI</h4>
              <p>Each message is sent to the Goala RAG system, which generates intelligent responses based on your documents.</p>
            </div>
          </div>
          <div className="work-item">
            <div className="work-icon">💬</div>
            <div className="work-content">
              <h4>Sends Responses</h4>
              <p>The bot automatically replies to messages after a brief delay (2-5 seconds) to appear more natural.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="info-section">
        <h3>Important Notes</h3>
        <ul className="notes-list">
          <li>The bot runs in a visible Chrome window for maximum stealth and reliability.</li>
          <li>All conversations are logged to the database with source='messenger' for tracking.</li>
          <li>You can pause the bot at any time to stop processing new messages without shutting it down.</li>
          <li>The bot will continue running 24/7 until manually stopped.</li>
          <li>Make sure your Facebook account remains logged in to Messenger.</li>
        </ul>
      </div>
    </div>
  );
};

export default MessengerPage;
