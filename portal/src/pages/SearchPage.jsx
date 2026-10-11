import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function SearchPage() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = () => {
    navigate(`/random-result?q=${encodeURIComponent(query)}`);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="search-page-container">
      <h2>Random Search</h2>
      <p>Find a single random media file where the filename or EXIF data matches your query.</p>
      <div className="search-controls">
        <label htmlFor="search-input" className="visually-hidden">Search filename or EXIF</label>
        <input
          id="search-input"
          type="text"
          className="filter-input"
          placeholder="e.g., 'artist_name' or 'landscape'..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button
          onClick={handleSearch}
          className="shuffle-button"
          aria-label="Find random media"
        >
          Find Random Media
        </button>
      </div>
      <p className="search-tip">Leave blank and click to browse all random media.</p>
    </div>
  );
}

export default SearchPage;