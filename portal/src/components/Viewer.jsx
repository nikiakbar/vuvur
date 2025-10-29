import React, { useState, useEffect, useRef } from 'react';
import MediaSlide from './MediaSlide';

// Removed the separate close button element from here
const Viewer = ({ files, initialIndex, onClose, onLike, onDelete, zoomLevel }) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);

  // Effect to handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
      if (e.key === 'd' || e.key === 'D') {
         if (onDelete && files && files.length > currentIndex && currentIndex >= 0) {
             const fileToDelete = files[currentIndex];
             if (fileToDelete && fileToDelete.id) {
                 console.log(`Delete key pressed for file ID: ${fileToDelete.id}`); // Optional: Add log
                 onDelete(fileToDelete.id);
             }
         }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onDelete, files, currentIndex]);


  // Effect to scroll to the initial index when opened
  useEffect(() => {
     const timer = setTimeout(() => {
        slideRefs.current[initialIndex]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
     }, 100);
     return () => clearTimeout(timer);
  }, [initialIndex]);

  // Effect to observe which slide is currently visible
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = parseInt(entry.target.dataset.index, 10);
          if (!isNaN(index) && index !== currentIndex) {
             console.log("Setting current index to:", index);
            setCurrentIndex(index);
          }
        }
      });
    }, { root: container, threshold: 0.7 });

    const refs = slideRefs.current;
    refs.forEach((ref) => { if (ref) observer.observe(ref) });

    return () => { refs.forEach((ref) => { if (ref) observer.unobserve(ref) }) };
  }, [files, currentIndex]);

  if (!files || files.length === 0) return null;

  return (
    // The separate close button element that was here is now removed
    <div className="viewer-overlay" ref={scrollContainerRef}>
      {/* The top-right close button is gone */}

      {files.map((file, index) => (
        <div key={file.id || file.path || index} ref={(el) => (slideRefs.current[index] = el)} data-index={index}>
          <MediaSlide
            file={file}
            index={index}
            currentIndex={currentIndex}
            onLike={() => onLike(file.id)}
            onDelete={() => onDelete(file.id)}
            onClose={onClose} // ✅ Pass onClose down to MediaSlide
            showControls={true}
            zoomLevel={zoomLevel || 2.5}
          />
        </div>
      ))}
    </div>
  );
};

export default Viewer;