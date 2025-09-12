import React, { useState, useEffect } from 'react';
import { useSettings } from '../contexts/SettingsContext';

function SettingsPage() {
  const { settings, lockedKeys, saveSettings, isLoading } = useSettings();
  const [localSettings, setLocalSettings] = useState(settings);
  const [message, setMessage] = useState('');
  const [isCleaning, setIsCleaning] = useState(false);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const handleSettingChange = (key, value) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    const numericSettings = {
      scan_interval: parseInt(localSettings.scan_interval),
      batch_size: parseInt(localSettings.batch_size),
      preload_count: parseInt(localSettings.preload_count),
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

  if (isLoading) {
    return <div>Loading settings...</div>;
  }

  return (
    <div className="settings-page">
      <h2>Settings</h2>
      
      <div className="settings-section">
        <h3>Performance & View Settings</h3>
        <div className="setting-option">
          <label htmlFor="batch-size-input">Gallery images per scroll</label>
          <input
            type="number" id="batch-size-input"
            value={localSettings.batch_size}
            onChange={(e) => handleSettingChange('batch_size', e.target.value)}
            min="1" step="5" disabled={lockedKeys.includes('batch_size')}
          />
        </div>
        {lockedKeys.includes('batch_size') && <small className="setting-warning">This setting is locked by your server environment.</small>}
        
        <div className="setting-option">
          <label htmlFor="preload-input">Random page preload count</label>
          <input
            type="number" id="preload-input"
            value={localSettings.preload_count}
            onChange={(e) => handleSettingChange('preload_count', e.target.value)}
            min="0" step="1" disabled={lockedKeys.includes('preload_count')}
          />
        </div>
        {lockedKeys.includes('preload_count') && <small className="setting-warning">This setting is locked by your server environment.</small>}

        <div className="setting-option">
          <label htmlFor="zoom-input">Viewer click-zoom level</label>
          <input
            type="number" id="zoom-input"
            value={localSettings.zoom_level}
            onChange={(e) => handleSettingChange('zoom_level', e.target.value)}
            min="1.1" step="0.1" disabled={lockedKeys.includes('zoom_level')}
          />
        </div>
        {lockedKeys.includes('zoom_level') && <small className="setting-warning">This setting is locked by your server environment.</small>}
      </div>

       <div className="settings-section">
        <h3>System Settings</h3>
         <div className="setting-option">
          <label htmlFor="scan-interval-input">Scan interval (seconds)</label>
          <input
            type="number" id="scan-interval-input"
            value={localSettings.scan_interval}
            onChange={(e) => handleSettingChange('scan_interval', e.target.value)}
            min="0" step="60" disabled={lockedKeys.includes('scan_interval')}
          />
        </div>
        <small>Set to 0 to disable periodic scanning. Requires a manual cache clean to trigger a new scan.</small>
        {lockedKeys.includes('scan_interval') && <small className="setting-warning">This setting is locked by your server environment.</small>}
        <br/><br/>
        <button onClick={handleSave} className="cleanup-button">Save Settings</button>
      </div>
      
      <div className="settings-section">
        <h3>System Cache</h3>
        <p>This will delete all cached media and the database. A new library scan will start automatically.</p>
        <button onClick={handleCleanup} disabled={isCleaning} className="cleanup-button">
          {isCleaning ? 'Cleaning...' : 'Clear All Caches & Re-Scan'}
        </button>
        {message && <p className="cleanup-message">{message}</p>}
      </div>
    </div>
  );
}

export default SettingsPage;