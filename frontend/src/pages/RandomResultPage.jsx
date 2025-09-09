import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import MediaSlide from '../components/MediaSlide';

function RandomResultPage({ showFullSize, zoomLevel }) {
  const [media, setMedia] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';

  useEffect(() => {
    // This effect runs whenever the query in the URL changes
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
  }, [query]); // Re-fetch if the URL query changes

  // Add the 'no-scroll' class to the body
  useEffect(() => {
    document.body.classList.add('no-scroll');
    return () => {
      document.body.classList.remove('no-scroll');
    };
  }, []);

  if (isLoading) {
    return <div className="loading-fullscreen">Searching...</div>;
  }

  if (error) {
    return <div className="loading-fullscreen">{error}</div>;
  }

  if (!media) {
    return <div className="loading-fullscreen">No media found.</div>;
  }

  // Render just the fullscreen media slide, with no controls
  return (
    <div className="viewer-overlay standalone-page fullscreen">
      <div className="viewer-slide">
        <MediaSlide
          file={media}
          showControls={false}
          showFullSize={true} // Always show full/preview size
          zoomLevel={zoomLevel}
        />
      </div>
    </div>
  );
}

export default RandomResultPage;