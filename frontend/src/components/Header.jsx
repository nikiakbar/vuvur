import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function Header({ currentTheme, toggleTheme }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const closeMenu = () => setIsMenuOpen(false);

  return (
    <header className="app-header">
      <Link to="/" className="logo-link">
        <svg className="logo-svg" viewBox="0 0 100 80" width="40" height="40">
            <rect width="100" height="80" rx="8" fill="var(--logo-bg)"/>
            <rect x="15" y="15" width="70" height="50" fill="var(--logo-accent)" />
            <circle cx="35" cy="35" r="10" fill="var(--logo-bg)" />
            <polygon points="55,55 75,25 90,45 80,65" fill="var(--logo-bg)" />
        </svg>
        <span className="logo-text">Vuvur</span>
      </Link>
      
      <div className="header-actions">
        <Link to="/random" className="header-action-button">
          Random
        </Link>
        <div className="menu-container">
          <button className="hamburger-button" onClick={() => setIsMenuOpen(!isMenuOpen)}>
            ☰
          </button>
          {isMenuOpen && (
            <div className="dropdown-menu">
              <button className="menu-item" onClick={toggleTheme}>
                Toggle {currentTheme === 'light' ? 'Dark' : 'Light'} Mode
              </button>
              <Link to="/settings" className="menu-item" onClick={closeMenu}>
                Settings
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;