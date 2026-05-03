import React, { useState, useEffect, useRef } from 'react';
import MediaSlide from './MediaSlide';

const Viewer = ({ files, initialIndex, onClose, onLike, onDelete, zoomLevel }) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);

  // Preload adjacent images
  useEffect(() => {
    const nextIndex = Math.min(currentIndex + 1, files.length - 1);
    const prevIndex = Math.max(currentIndex - 1, 0);
    
    // Simple image preloader
    const preload = (index) => {
      if (files[index] && files[index].type === 'image') {
        const img = new Image();
        img.src = `/api/stream/${files[index].id}`;
      }
    };
    
    preload(nextIndex);
    preload(prevIndex);
  }, [currentIndex, files]);

  // Effect to handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      
      // Navigation
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault();
        setCurrentIndex(prev => Math.min(prev + 1, files.length - 1));
      } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault();
        setCurrentIndex(prev => Math.max(prev - 1, 0));
      }

      // Actions
      if (e.key === 'd' || e.key === 'D') {
         if (onDelete && files && files.length > currentIndex && currentIndex >= 0) {
             onDelete(files[currentIndex].id);
         }
      }
      if (e.key === 'l' || e.key === 'L') {
        if (onLike && files && files.length > currentIndex && currentIndex >= 0) {
            onLike(files[currentIndex].id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onDelete, onLike, files, currentIndex]); 

  // Touch handling for swiping
  const touchStartY = useRef(0);
  
  const handleTouchStart = (e) => {
    touchStartY.current = e.touches[0].clientY;
  };
  
  const handleTouchEnd = (e) => {
    const touchEndY = e.changedTouches[0].clientY;
    const diff = touchStartY.current - touchEndY;
    
    // Swipe up -> next image
    if (diff > 50) {
      setCurrentIndex(prev => Math.min(prev + 1, files.length - 1));
    } 
    // Swipe down -> prev image
    else if (diff < -50) {
      setCurrentIndex(prev => Math.max(prev - 1, 0));
    }
  };

  // Mouse wheel handling
  const isWheeling = useRef(false);
  const handleWheel = (e) => {
    if (isWheeling.current) return;
    
    // Only trigger on significant scroll delta
    if (Math.abs(e.deltaY) > 20) {
      isWheeling.current = true;
      if (e.deltaY > 0) {
        setCurrentIndex(prev => Math.min(prev + 1, files.length - 1));
      } else {
        setCurrentIndex(prev => Math.max(prev - 1, 0));
      }
      
      // Cooldown to prevent trackpad hyper-scrolling
      setTimeout(() => {
        isWheeling.current = false;
      }, 500); 
    }
  };

  if (!files || files.length === 0) return null;

  const currentFile = files[currentIndex];

  return (
    <div 
      className="viewer-overlay" 
      style={{ overflow: 'hidden' }} // Force disable all native scrolling
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onWheel={handleWheel}
    >
      <div style={{ height: '100vh', width: '100%', position: 'relative' }}>
        <MediaSlide
          key={currentFile.id || currentIndex} // Force re-render on change
          file={currentFile}
          index={currentIndex}
          currentIndex={currentIndex}
          onLike={() => onLike(currentFile.id)}
          onDelete={() => onDelete(currentFile.id)} 
          onClose={onClose} 
          showControls={true}
          zoomLevel={zoomLevel || 2.5}
        />
      </div>
      
      {/* Navigation Indicators */}
      <div className="viewer-nav-indicator top" onClick={() => setCurrentIndex(prev => Math.max(prev - 1, 0))}>
        {currentIndex > 0 && <span className="arrow up-arrow">▲</span>}
      </div>
      <div className="viewer-nav-indicator bottom" onClick={() => setCurrentIndex(prev => Math.min(prev + 1, files.length - 1))}>
        {currentIndex < files.length - 1 && <span className="arrow down-arrow">▼</span>}
      </div>
    </div>
  );
};

export default Viewer;