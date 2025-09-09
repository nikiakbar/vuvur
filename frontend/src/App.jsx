import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import GalleryPage from './pages/GalleryPage';
import SettingsPage from './pages/SettingsPage';
import RandomPage from './pages/RandomPage';
import RandomResultPage from './pages/RandomResultPage';

function getInitialSetting(envVarName, storageKey, defaultValue) {
  const envValue = (window.env && window.env[envVarName]) ? window.env[envVarName] : "";

  if (envValue && envValue !== "") {
    return { value: parseFloat(envValue), isLocked: true };
  }
  const storedValue = localStorage.getItem(storageKey);
  if (storedValue) {
    return { value: parseFloat(storedValue), isLocked: false };
  }
  return { value: defaultValue, isLocked: false };
}

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [batchSizeSetting, setBatchSizeSetting] = useState(
    getInitialSetting('GALLERY_BATCH_SIZE', 'batchSize', 20)
  );
  const [preloadCountSetting, setPreloadCountSetting] = useState(
    getInitialSetting('RANDOM_PRELOAD_COUNT', 'preloadCount', 3)
  );
  const [zoomLevelSetting, setZoomLevelSetting] = useState(
    getInitialSetting('ZOOM_LEVEL', 'zoomLevel', 2.5)
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

  const handleBatchSizeChange = (newSize) => {
    if (batchSizeSetting.isLocked) return;
    const size = parseInt(newSize);
    if (size > 0) {
      setBatchSizeSetting({ value: size, isLocked: false });
      localStorage.setItem('batchSize', size);
    }
  };

  const handlePreloadCountChange = (newSize) => {
    if (preloadCountSetting.isLocked) return;
    const size = parseInt(newSize);
    if (size >= 0) {
      setPreloadCountSetting({ value: size, isLocked: false });
      localStorage.setItem('preloadCount', size);
    }
  };

  const handleZoomLevelChange = (newZoom) => {
    if (zoomLevelSetting.isLocked) return;
    const zoom = parseFloat(newZoom);
    if (zoom > 1.0) {
      setZoomLevelSetting({ value: zoom, isLocked: false });
      localStorage.setItem('zoomLevel', zoom);
    }
  };

  const location = useLocation();
  const isFullscreen = location.pathname === '/random' || location.pathname === '/random-result';

  return (
    <div className="app-container">
      {!isFullscreen && <Header currentTheme={theme} toggleTheme={toggleTheme} />}
      
      <main className={!isFullscreen ? "main-content" : "main-content-full"}>
        <Routes>
          <Route 
            path="/" 
            element={<GalleryPage 
              batchSize={batchSizeSetting.value} 
              showFullSize={showFullSize} 
              setShowFullSize={setShowFullSize} 
              zoomLevel={zoomLevelSetting.value}
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
              zoomLevel={zoomLevelSetting.value}
              onZoomLevelChange={handleZoomLevelChange}
              isZoomLevelLocked={zoomLevelSetting.isLocked}
            />} 
          />
          <Route 
            path="/random" 
            element={<RandomPage 
              showFullSize={showFullSize} 
              preloadCount={preloadCountSetting.value} 
              zoomLevel={zoomLevelSetting.value}
            />} 
          />
          <Route 
            path="/random-result"
            element={<RandomResultPage
              showFullSize={showFullSize}
              zoomLevel={zoomLevelSetting.value}
            />}
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;