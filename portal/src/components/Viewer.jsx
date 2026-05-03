import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import MediaSlide from './MediaSlide';

const Viewer = ({ files, initialIndex, onClose, onLike, onDelete, zoomLevel }) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);
  const isScrollingRef = useRef(true);

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
                 onDelete(fileToDelete.id);
             }
         }
      }
      // Add 'l' key listener for like
      if (e.key === 'l' || e.key === 'L') {
        if (onLike && files && files.length > currentIndex && currentIndex >= 0) {
            const fileToLike = files[currentIndex];
            if (fileToLike && fileToLike.id) {
                onLike(fileToLike.id);
            }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    // Cleanup function to remove listener
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onDelete, files, currentIndex]); // Added dependencies


  // Effect to scroll to the initial index when opened
  useLayoutEffect(() => {
    if (!scrollContainerRef.current) return;
    
    isScrollingRef.current = true;
    // Disable snapping temporarily to prevent the browser from fighting the programmatic scroll
    scrollContainerRef.current.style.scrollSnapType = 'none';
    
    const containerHeight = scrollContainerRef.current.clientHeight;
    scrollContainerRef.current.scrollTop = initialIndex * containerHeight;
    
    if (slideRefs.current[initialIndex]) {
      slideRefs.current[initialIndex].scrollIntoView({ block: 'start', behavior: 'auto' });
    }

    const timer = setTimeout(() => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.style.scrollSnapType = ''; // Restore CSS default
      }
      isScrollingRef.current = false;
    }, 100);
    
    return () => clearTimeout(timer);
  }, [initialIndex]); // Only run when initialIndex changes

  // Effect to observe which slide is currently visible
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !isScrollingRef.current) {
          const index = parseInt(entry.target.dataset.index, 10);
          if (!isNaN(index) && index !== currentIndex) { // Only update if index actually changes
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

  // ⚡ Bolt: Virtualization optimization.
  // We only render the current slide and its immediate neighbors to reduce DOM size and React overhead.
  // This prevents O(N) rendering where N is the number of items in the gallery.
  // A buffer of 2 on each side ensures smooth scrolling while keeping component count minimal.
  const VIRTUAL_BUFFER = 2;

  return (
    <div className="viewer-overlay" ref={scrollContainerRef}>
      {/* The top-right close button is gone */}

      {files.map((file, index) => {
        const isVisible = Math.abs(index - currentIndex) <= VIRTUAL_BUFFER || index === initialIndex;

        return (
          // We MUST keep the wrapper div rendered to maintain the scroll height and snapping points.
          <div 
            key={file.id || file.path || index} 
            ref={(el) => (slideRefs.current[index] = el)} 
            data-index={index}
            style={{ flex: '0 0 100%', width: '100%', scrollSnapAlign: 'start' }}
          >
            {isVisible && (
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
            )}
          </div>
        );
      })}
    </div>
  );
};

export default Viewer;