import React, { useState, useEffect, useRef } from 'react';
import MediaSlide from './MediaSlide';

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
      // Add 'd' key listener for delete
      if (e.key === 'd' || e.key === 'D') {
         // Check if onDelete function exists and files array is valid
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
    // Cleanup function to remove listener
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onDelete, files, currentIndex]); // Added dependencies


  // Effect to scroll to the initial index when opened
  useEffect(() => {
     // Delay scrolling slightly to ensure layout is complete
     const timer = setTimeout(() => {
        // ✅ Changed behavior from 'smooth' to 'auto' for an instant jump
        slideRefs.current[initialIndex]?.scrollIntoView({ block: 'center', behavior: 'auto' });
     }, 100); // 100ms delay
     return () => clearTimeout(timer); // Cleanup timer
  }, [initialIndex]); // Only run when initialIndex changes

  // Effect to observe which slide is currently visible
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = parseInt(entry.target.dataset.index, 10);
          if (!isNaN(index) && index !== currentIndex) { // Only update if index actually changes
             console.log("Setting current index to:", index); // Optional log
            setCurrentIndex(index);
          }
        }
      });
    }, { root: container, threshold: 0.7 }); // Trigger when 70% visible

    const refs = slideRefs.current;
    refs.forEach((ref) => { if (ref) observer.observe(ref) });

    // Cleanup observer
    return () => { refs.forEach((ref) => { if (ref) observer.unobserve(ref) }) };
  }, [files, currentIndex]);

  if (!files || files.length === 0) return null;

  return (
    <div className="viewer-overlay" ref={scrollContainerRef}>
      {/* The top-right close button is gone */}

      {files.map((file, index) => (
        // Ensure each slide div has a unique key and the data-index attribute
        <div key={file.id || file.path || index} ref={(el) => (slideRefs.current[index] = el)} data-index={index}>
          <MediaSlide
            file={file}
            index={index}
            currentIndex={currentIndex} // Pass current index to MediaSlide
            onLike={() => onLike(file.id)}
            onDelete={() => onDelete(file.id)} // Pass direct delete handler for button
            onClose={onClose} // Pass onClose down to MediaSlide
            showControls={true}
            zoomLevel={zoomLevel || 2.5}
          />
        </div>
      ))}
    </div>
  );
};

export default Viewer;