import React, { createContext, useState, useContext } from 'react';

// Define the default settings for the frontend
const defaultSettings = {
  zoom_level: 2.5,
  // You can add other frontend-specific settings here in the future
};

// Function to load settings from the browser's local storage
const loadSettingsFromStorage = () => {
  try {
    const storedSettings = localStorage.getItem('vuvur-settings');
    // Merge stored settings with defaults to ensure all keys are present
    return storedSettings ? { ...defaultSettings, ...JSON.parse(storedSettings) } : defaultSettings;
  } catch (error) {
    console.error("Failed to parse settings from local storage:", error);
    return defaultSettings;
  }
};

// Create the context
const SettingsContext = createContext(null);

// Create the provider component
export const SettingsProvider = ({ children }) => {
  const [settings, setSettings] = useState(loadSettingsFromStorage);

  // Function to save settings to state and local storage
  const saveSettings = (newSettings) => {
    try {
      const settingsToSave = { ...settings, ...newSettings };
      localStorage.setItem('vuvur-settings', JSON.stringify(settingsToSave));
      setSettings(settingsToSave);
    } catch (error) {
      console.error("Failed to save settings to local storage:", error);
    }
  };

  const value = { settings, saveSettings };

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