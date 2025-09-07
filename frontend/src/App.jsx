import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import GalleryPage from './pages/GalleryPage';
import SettingsPage from './pages/SettingsPage';
import RandomPage from './pages/RandomPage';

// --- Helper function to read settings based on priority ---
function getInitialSetting(envVarName, storageKey, defaultValue) {
  const envValue = window.env[envVarName];
  if (envValue && envValue !== "") {
    // 1. Docker environment variable has highest priority
    return { value: parseInt(envValue), isLocked: true };
  }
  const storedValue = localStorage.getItem(storageKey);
  if (storedValue) {
    // 2. User's saved setting is next
    return { value: parseInt(storedValue), isLocked: false };
  }
  // 3. Fallback to hardcoded default
  return { value: defaultValue, isLocked: false };
}

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  
  // --- Initialize settings using our new priority logic ---
  const [batchSizeSetting, setBatchSizeSetting] = useState(
    getInitialSetting('GALLERY_BATCH_SIZE', 'batchSize', 20)
  );
  const [preloadCountSetting, setPreloadCountSetting] = useState(
    getInitialSetting('RANDOM_PRELOAD_COUNT', 'preloadCount', 3)
  );
  const [showFullSize, setShowFullSize] = useState(false);

  useEffect(() => {
    document.body.className = '';
    document.body.classList.add(`${theme}-theme`);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  // --- Handlers will now only save to storage if the setting is NOT locked by Docker ---
  const handleBatchSizeChange = (newSize) => {
    if (batchSizeSetting.isLocked) return; // Do nothing if locked
    const size = parseInt(newSize);
    if (size > 0) {
      setBatchSizeSetting({ value: size, isLocked: false });
      localStorage.setItem('batchSize', size);
    }
  };

  const handlePreloadCountChange = (newSize) => {
    if (preloadCountSetting.isLocked) return; // Do nothing if locked
    const size = parseInt(newSize);
    if (size >= 0) {
      setPreloadCountSetting({ value: size, isLocked: false });
      localStorage.setItem('preloadCount', size);
    }
  };

  const location = useLocation();
  const isRandomPage = location.pathname === '/random';

  return (
    <div className="app-container">
      {!isRandomPage && <Header currentTheme={theme} toggleTheme={toggleTheme} />}
      
      <main className={!isRandomPage ? "main-content" : "main-content-full"}>
        <Routes>
          <Route 
            path="/" 
            element={<GalleryPage 
              batchSize={batchSizeSetting.value} 
              showFullSize={showFullSize} 
              setShowFullSize={setShowFullSize} 
            />} 
          />
          <Route 
            path="/settings" 
            element={<SettingsPage 
              batchSize={batchSizeSetting.value} 
              onBatchSizeChange={handleBatchSizeChange}
              isBatchSizeLocked={batchSizeSetting.isLocked}
              preloadCount={preloadCountSetting.value}
              onPreloadCountChange={handlePreloadCountChange}
              isPreloadCountLocked={preloadCountSetting.isLocked}
            />} 
          />
          <Route 
            path="/random" 
            element={<RandomPage 
              showFullSize={showFullSize} 
              preloadCount={preloadCountSetting.value} 
            />} 
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;