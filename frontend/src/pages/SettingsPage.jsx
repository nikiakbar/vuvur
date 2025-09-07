import React, { useState } from 'react';

function SettingsPage({ batchSize, onBatchSizeChange }) {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleCleanup = async () => {
    setIsLoading(true);
    setMessage('Clearing all caches and triggering library re-scan...');
    try {
      const response = await fetch('/api/cache/cleanup', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to clean cache.');
      }
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
        <h3>Gallery Settings</h3>
        <div className="setting-option">
          <label htmlFor="batch-size-input">Images per scroll</label>
          <input
            type="number"
            id="batch-size-input"
            value={batchSize}
            onChange={(e) => onBatchSizeChange(e.target.value)}
            min="1"
            step="5"
          />
        </div>
      </div>
      
      <div className="settings-section">
        <h3>System Cache</h3>
        <p>
          This will delete all cached thumbnails, previews, and the main file list. 
          A new scan of your library will start automatically.
        </p>
        <button onClick={handleCleanup} disabled={isLoading} className="cleanup-button">
          {isLoading ? 'Cleaning...' : 'Clear All Caches & Re-Scan'}
        </button>
        {message && <p className="cleanup-message">{message}</p>}
      </div>
    </div>
  );
}

export default SettingsPage;