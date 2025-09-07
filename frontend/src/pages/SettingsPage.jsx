import React, { useState } from 'react';

function SettingsPage({ 
  batchSize, onBatchSizeChange, isBatchSizeLocked,
  preloadCount, onPreloadCountChange, isPreloadCountLocked,
  zoomLevel, onZoomLevelChange, isZoomLevelLocked
}) {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleCleanup = async () => {
    // ... (cleanup logic is unchanged) ...
    setIsLoading(true);
    setMessage('Clearing all caches and triggering library re-scan...');
    try {
      const response = await fetch('/api/cache/cleanup', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to clean cache.');
      setMessage(data.message);
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="settings-page">
      <h2>Settings</h2>
      
      <div className="settings-section">
        <h3>Performance & View Settings</h3>
        <div className="setting-option">
          <label htmlFor="batch-size-input">Gallery images per scroll</label>
          <input
            type="number" id="batch-size-input"
            value={batchSize} onChange={(e) => onBatchSizeChange(e.target.value)}
            min="1" step="5" disabled={isBatchSizeLocked}
          />
        </div>
        {isBatchSizeLocked && <small className="setting-warning">This setting is locked by your server environment.</small>}
        
        <div className="setting-option">
          <label htmlFor="preload-input">Random page preload count</label>
          <input
            type="number" id="preload-input"
            value={preloadCount} onChange={(e) => onPreloadCountChange(e.target.value)}
            min="0" step="1" disabled={isPreloadCountLocked}
          />
        </div>
        {isPreloadCountLocked && <small className="setting-warning">This setting is locked by your server environment.</small>}

        <div className="setting-option">
          <label htmlFor="zoom-input">Viewer click-zoom level</label>
          <input
            type="number" id="zoom-input"
            value={zoomLevel} onChange={(e) => onZoomLevelChange(e.target.value)}
            min="1.1" step="0.1" disabled={isZoomLevelLocked}
          />
        </div>
        {isZoomLevelLocked && <small className="setting-warning">This setting is locked by your server environment.</small>}
      </div>
      
      <div className="settings-section">
        <h3>System Cache</h3>
        <p>This will delete all cached media and the file list. A new library scan will start automatically.</p>
        <button onClick={handleCleanup} disabled={isLoading} className="cleanup-button">
          {isLoading ? 'Cleaning...' : 'Clear All Caches & Re-Scan'}
        </button>
        {message && <p className="cleanup-message">{message}</p>}
      </div>
    </div>
  );
}

export default SettingsPage;