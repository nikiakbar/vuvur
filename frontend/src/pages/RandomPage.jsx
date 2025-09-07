import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import MediaSlide from '../components/MediaSlide';

// Read values from the global window.env object, with defaults
const PRELOAD_COUNT = parseInt(window.env.VITE_RANDOM_PRELOAD_COUNT || 3);
const HISTORY_SIZE = parseInt(window.env.VITE_RANDOM_HISTORY_SIZE || 5);
const MAX_QUEUE_SIZE = HISTORY_SIZE + 1 + PRELOAD_COUNT;

function RandomPage({ showFullSize }) {
  const [filesQueue, setFilesQueue] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const observer = useRef();

  const fetchRandomFiles = useCallback(async (count) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/files/random?count=${count}`);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      if (data.length > 0) {
        setFilesQueue(prevFiles => {
          const newFiles = [...prevFiles, ...data];
          // Trim the history if the queue is now too long
          if (newFiles.length > MAX_QUEUE_SIZE) {
            return newFiles.slice(newFiles.length - MAX_QUEUE_SIZE);
          }
          return newFiles;
        });
        // Adjust current index if we trimmed the history
        if (filesQueue.length > MAX_QUEUE_SIZE) {
          setCurrentIndex(prev => Math.max(0, prev - (filesQueue.length - MAX_QUEUE_SIZE)));
        }
      }
    } catch (error) {
      console.error("Failed to fetch random file:", error);
    } finally {
      setIsLoading(false);
    }
  }, [filesQueue.length]);

  useEffect(() => {
    const slideNodes = document.querySelectorAll('.viewer-slide');
    if (slideNodes.length === 0) return;
    const preloadTriggerIndex = Math.max(0, filesQueue.length - PRELOAD_COUNT + 1);
    const nodeToObserve = slideNodes[preloadTriggerIndex];

    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && !isLoading) {
        fetchRandomFiles(PRELOAD_COUNT);
      }
    });
    if (nodeToObserve) {
      observer.current.observe(nodeToObserve);
    }
    return () => { if (nodeToObserve) observer.current.unobserve(nodeToObserve) };
  }, [filesQueue.length, isLoading, fetchRandomFiles]);

  useEffect(() => {
    document.body.classList.add('no-scroll');
    fetchRandomFiles(1 + PRELOAD_COUNT);
    return () => { document.body.classList.remove('no-scroll') };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 

  if (filesQueue.length === 0 && isLoading) {
    return <div className="loading-fullscreen">Loading...</div>;
  }
  if (filesQueue.length === 0 && !isLoading) {
    return <div className="loading-fullscreen">No media found.</div>;
  }

  return (
    <div className="viewer-overlay standalone-page fullscreen">
      <Link to="/" className="close-button standalone-close-button" title="Back to Gallery">&times;</Link>
      {filesQueue.map((file, index) => (
        <div key={file.path} className="viewer-slide">
          <MediaSlide 
            file={file} 
            showControls={false} 
            showFullSize={true} 
          />
        </div>
      ))}
      {isLoading && <div className="loading-spinner"></div>}
    </div>
  );
}

export default RandomPage;