import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import GalleryPage from './pages/GalleryPage';
import RandomPage from './pages/RandomPage';
import RandomResultPage from './pages/RandomResultPage';
import SearchPage from './pages/SearchPage';

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [showFullSize, setShowFullSize] = useState(false);

  useEffect(() => {
    document.body.className = '';
    document.body.classList.add(`${theme}-theme`);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  const location = useLocation();
  const isFullscreen = location.pathname === '/random-scroller' || location.pathname === '/random-result';

  return (
    <div className="app-container">
      {!isFullscreen && <Header currentTheme={theme} toggleTheme={toggleTheme} />}

      <main className={!isFullscreen ? "main-content" : "main-content-full"}>
        <Routes>
          <Route
            path="/"
            element={<GalleryPage
              showFullSize={showFullSize}
              setShowFullSize={setShowFullSize}
            />}
          />
          <Route
            path="/random-scroller"
            element={<RandomPage
              showFullSize={showFullSize}
            />}
          />
          <Route
            path="/search"
            element={<SearchPage />}
          />
          <Route
            path="/random-result"
            element={<RandomResultPage
              showFullSize={showFullSize}
            />}
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;