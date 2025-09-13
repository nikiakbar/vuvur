import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';

function RandomResultPage({ showFullSize, zoomLevel }) {
  const [media, setMedia] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';

  useEffect(() => {
    const fetchMedia = async () => {
      setIsLoading(true);
      setError('');
      setMedia(null);
      try {
        const response = await fetch(`/api/random-single?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        if (!response.ok || data.length === 0) {
          throw new Error(data.error || 'No media found matching that query.');
        }
        setMedia(data[0]);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchMedia();
  }, [query]);

  useEffect(() => {
    document.body.classList.add('no-scroll');
    return () => {
      document.body.classList.remove('no-scroll');
    };
  }, []);

  const containerClass = media?.type === 'video' ? 'result-video-container' : 'result-image-container';

  return (
    <div className="fullscreen-result-page">
      {isLoading && <div className="loading-fullscreen">Searching...</div>}
      {error && <div className="loading-fullscreen">{error} <Link to="/search" className="inline-link">Try another search?</Link></div>}
      
      {media && (
        <div className={containerClass}>
          {media.type === 'image' ? (
            <img src={`/api/stream/${media.id}`} alt={media.path} />
          ) : (
            <video src={`/api/stream/${media.id}`} controls autoPlay loop />
          )}
        </div>
      )}
    </div>
  );
}

export default RandomResultPage;