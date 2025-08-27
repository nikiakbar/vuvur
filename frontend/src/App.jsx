import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import GalleryPage from './pages/GalleryPage';
import SettingsPage from './pages/SettingsPage';
import RandomPage from './pages/RandomPage';

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const location = useLocation(); // Get the current route location

  useEffect(() => {
    document.body.className = '';
    document.body.classList.add(`${theme}-theme`);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  // Check if the current page is the random page
  const isRandomPage = location.pathname === '/random';

  return (
    <div className="app-container">
      {/* Conditionally render the Header */}
      {!isRandomPage && <Header currentTheme={theme} toggleTheme={toggleTheme} />}
      
      <main className={!isRandomPage ? "main-content" : "main-content-full"}>
        <Routes>
          <Route path="/" element={<GalleryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/random" element={<RandomPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;