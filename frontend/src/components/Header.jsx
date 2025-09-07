import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function Header({ currentTheme, toggleTheme }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const closeMenu = () => setIsMenuOpen(false);

  return (
    <header className="app-header">
      <Link to="/" className="logo-link">
        <img src="/logo.png" height="40" alt="Vuvur Logo" />
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