import React, { useState } from 'react';
import { useSettings } from '../contexts/SettingsContext';

function SettingsPage() {
  const { settings, saveSettings } = useSettings();
  const [localSettings, setLocalSettings] = useState(settings);
  const [message, setMessage] = useState('');
  const [isCleaning, setIsCleaning] = useState(false);

  const handleSettingChange = (key, value) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    // Ensure zoom_level is saved as a number
    const numericSettings = {
      zoom_level: parseFloat(localSettings.zoom_level)
    };
    saveSettings(numericSettings);
    setMessage('Settings saved!');
    setTimeout(() => setMessage(''), 2000);
  };

  const handleCleanup = async () => {
    setIsCleaning(true);
    setMessage('Clearing all caches and triggering library re-scan...');
    try {
      const response = await fetch('/api/cache/cleanup', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed.');
      setMessage(data.message);
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setIsCleaning(false);
    }
  };

  return (
    <div className="settings-page">
      <h2>Settings</h2>
      
      <div className="settings-section">
        <h3>View Settings</h3>
        <div className="setting-option">
          <label htmlFor="zoom-input">Viewer click-zoom level</label>
          <input
            type="number" id="zoom-input"
            value={localSettings.zoom_level}
            onChange={(e) => handleSettingChange('zoom_level', e.target.value)}
            min="1.1" step="0.1"
          />
        </div>
         <br/>
        <button onClick={handleSave} className="cleanup-button">Save Settings</button>
      </div>
      
      <div className="settings-section">
        <h3>System Cache</h3>
        <p>This will delete all cached media and the database. A new library scan will start automatically.</p>
        <button onClick={handleCleanup} disabled={isCleaning} className="cleanup-button">
          {isCleaning ? 'Cleaning...' : 'Clear Caches & Re-Scan'}
        </button>
        {message && <p className="cleanup-message">{message}</p>}
      </div>
    </div>
  );
}

export default SettingsPage;