import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import MediaSlide from '../components/MediaSlide';
import { useSettings } from '../contexts/SettingsContext'; // Import the hook

function RandomPage({ showFullSize }) {
  const { settings } = useSettings(); // Use the global settings
  const preloadCount = settings.preload_count;
  const zoomLevel = settings.zoom_level;

  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const observer = useRef();

  const loadNextImages = useCallback(async (count) => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const response = await fetch(`/api/files/random?count=${count}`);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      if (data.length > 0) {
        setFiles(prevFiles => [...prevFiles, ...data]);
      }
    } catch (error) { console.error("Failed to fetch random file:", error); } 
    finally { setIsLoading(false); }
  }, [isLoading]);
  
  const lastImageElementRef = useCallback(node => {
    if (isLoading) return;
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        loadNextImages(preloadCount);
      }
    });
    if (node) observer.current.observe(node);
  }, [isLoading, loadNextImages, preloadCount]);

  useEffect(() => {
    document.body.classList.add('no-scroll');
    loadNextImages(1 + preloadCount);
    return () => { document.body.classList.remove('no-scroll') };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 

  if (files.length === 0 && isLoading) { return <div className="loading-fullscreen">Loading...</div> }
  if (files.length === 0 && !isLoading) { return <div className="loading-fullscreen">No media found.</div> }

  return (
    <div className="viewer-overlay standalone-page fullscreen">
      <Link to="/" className="close-button standalone-close-button" title="Back to Gallery">&times;</Link>
      {files.map((file, index) => {
        const isLastElement = index === files.length - 1;
        return (
          <div ref={isLastElement ? lastImageElementRef : null} key={`${file.path}-${index}`} className="viewer-slide">
            <MediaSlide 
              file={file} 
              showControls={false} 
              showFullSize={true} 
              zoomLevel={zoomLevel} // Pass the setting
            />
          </div>
        );
      })}
      {isLoading && <div className="loading-spinner"></div>}
    </div>
  );
}

export default RandomPage;