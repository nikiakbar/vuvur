import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import GalleryPage from './pages/GalleryPage';
import SettingsPage from './pages/SettingsPage';
import RandomPage from './pages/RandomPage';

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [batchSize, setBatchSize] = useState(() => parseInt(localStorage.getItem('batchSize')) || 20);
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
    const size = parseInt(newSize);
    if (size > 0) {
      setBatchSize(size);
      localStorage.setItem('batchSize', size);
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
              batchSize={batchSize} 
              showFullSize={showFullSize} 
              setShowFullSize={setShowFullSize} 
            />} 
          />
          <Route 
            path="/settings" 
            element={<SettingsPage 
              batchSize={batchSize} 
              onBatchSizeChange={handleBatchSizeChange} 
            />} 
          />
          <Route 
            path="/random" 
            element={<RandomPage showFullSize={showFullSize} />} 
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;