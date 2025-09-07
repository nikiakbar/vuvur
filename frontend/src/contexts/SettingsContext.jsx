import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';

// Create the context
const SettingsContext = createContext(null);

// Create the provider component
export const SettingsProvider = ({ children }) => {
  const [settings, setSettings] = useState(null);
  const [lockedKeys, setLockedKeys] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Function to fetch settings from the backend
  const fetchSettings = useCallback(async () => {
    try {
      const response = await fetch('/api/settings');
      const data = await response.json();
      setSettings(data.settings);
      setLockedKeys(data.locked_keys);
    } catch (error) {
      console.error("Failed to load app settings:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch settings when the app first loads
  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // Function to save settings to the backend
  const saveSettings = async (newSettings) => {
    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings),
      });
      const data = await response.json();
      setSettings(data); // Set the returned (and validated) settings
    } catch (error) {
      console.error("Failed to save settings:", error);
    }
  };

  const value = {
    settings,
    lockedKeys,
    isLoading,
    saveSettings,
  };

  // Show a loading indicator until settings are fetched
  if (isLoading) {
    return <div className="loading-fullscreen">Loading Settings...</div>;
  }

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
};

// Custom hook to easily consume the settings
export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};