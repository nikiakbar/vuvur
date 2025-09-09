import React, { useState } from 'react';
import MediaSlide from '../components/MediaSlide';

function SearchPage({ showFullSize, zoomLevel }) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    setIsLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await fetch(`/api/random-single?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'File not found');
      }
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
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
        <input
          type="text"
          className="filter-input"
          placeholder="Search for 'artist' or '.png'..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button onClick={handleSearch} disabled={isLoading} className="shuffle-button">
          {isLoading ? 'Searching...' : 'Find Random File'}
        </button>
      </div>

      <div className="search-result-container">
        {isLoading && <div className="loading-spinner-inline" />}
        {error && <p className="search-error">{error}</p>}
        {result && (
          <div className="search-result-item">
            <MediaSlide
              file={result}
              showControls={false}
              showFullSize={showFullSize}
              zoomLevel={zoomLevel}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchPage;