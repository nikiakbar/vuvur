import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';

function RandomPage() {
  const [randomFiles, setRandomFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Add a class to the body to hide scrollbars when this component mounts
  useEffect(() => {
    document.body.classList.add('no-scroll');
    // Cleanup function to remove the class when the component unmounts
    return () => {
      document.body.classList.remove('no-scroll');
    };
  }, []);

  const fetchRandomFiles = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/files?sort=random');
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      setRandomFiles(data);
    } catch (error) {
      console.error("Failed to fetch random files:", error);
      setRandomFiles([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRandomFiles();
  }, [fetchRandomFiles]);

  if (isLoading) {
    return <div className="loading-fullscreen">Loading...</div>;
  }

  if (randomFiles.length === 0) {
    return <div className="loading-fullscreen">No images found.</div>;
  }

  return (
    <div className="viewer-overlay standalone-page fullscreen">
      {/* Add a subtle link/button to go back home */}
      <Link to="/" className="close-button standalone-close-button" title="Back to Gallery">
        &times;
      </Link>
      {randomFiles.map((file) => (
        <div key={file.path} className="viewer-slide">
          <div className="viewer-image-container">
            {/* Using the higher quality preview for the full-screen view */}
            <img src={`/api/preview/${encodeURIComponent(file.path)}`} alt={file.path} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default RandomPage;