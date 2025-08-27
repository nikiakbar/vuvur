import React, { useState } from 'react';

function SettingsPage() {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleCleanup = async () => {
    setIsLoading(true);
    setMessage('Cleaning up cache...');
    try {
      const response = await fetch('/api/cache/cleanup', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to clean cache.');
      }
      setMessage(`Cleanup successful! Deleted ${data.deleted_files} orphaned thumbnails.`);
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
        <h3>Thumbnail Cache</h3>
        <p>
          Remove cached thumbnails for source images that no longer exist.
        </p>
        <button onClick={handleCleanup} disabled={isLoading} className="cleanup-button">
          {isLoading ? 'Cleaning...' : 'Clean Thumbnail Cache'}
        </button>
        {message && <p className="cleanup-message">{message}</p>}
      </div>
    </div>
  );
}

export default SettingsPage;