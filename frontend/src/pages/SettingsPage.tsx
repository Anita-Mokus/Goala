import { useState, useEffect } from 'react';
import { apiClient, Settings, SettingsUpdate } from '../api/client';
import SettingsForm from '../components/SettingsForm';
import './SettingsPage.css';

function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getSettings();
      setSettings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (updatedSettings: SettingsUpdate) => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);
      const data = await apiClient.updateSettings(updatedSettings);
      setSettings(data);
      setSuccessMessage('Settings saved successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-page">
        <div className="loading">Loading settings...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="settings-page">
        <div className="error-message">
          <p>Error: {error}</p>
          <button onClick={loadSettings}>Retry</button>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="settings-page">
        <div className="error-message">No settings found</div>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <h1>Application Settings</h1>
      <p className="settings-description">
        Configure RAG parameters for your AI assistant. Note: API keys and sensitive
        credentials must be managed through environment variables.
      </p>

      {successMessage && (
        <div className="success-message">{successMessage}</div>
      )}

      {error && <div className="error-message">{error}</div>}

      <SettingsForm
        settings={settings}
        onSave={handleSave}
        saving={saving}
      />

      <div className="settings-footer">
        <small>Last updated: {new Date(settings.updated_at).toLocaleString()}</small>
      </div>
    </div>
  );
}

export default SettingsPage;
