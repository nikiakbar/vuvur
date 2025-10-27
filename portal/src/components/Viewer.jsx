import React, { useState, useEffect, useRef } from 'react';
import MediaSlide from './MediaSlide';

const Viewer = ({ files, initialIndex, onClose, onLike, onDelete, zoomLevel }) => { // Removed showFullSize
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);
  
  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose() };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    slideRefs.current[initialIndex]?.scrollIntoView({ block: 'center' });
  }, [initialIndex]);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = parseInt(entry.target.dataset.index, 10);
          if (!isNaN(index)) {
            setCurrentIndex(index);
          }
        }
      });
    }, { root: scrollContainerRef.current, threshold: 0.7 });

    const refs = slideRefs.current;
    refs.forEach((ref) => { if (ref) observer.observe(ref) });
    return () => { refs.forEach((ref) => { if (ref) observer.unobserve(ref) }) };
  }, [files]);
  
  if (files.length === 0) return null;

  return (
    <div className="viewer-overlay" ref={scrollContainerRef}>
      <button className="close-button" onClick={onClose}>&times;</button>

      {files.map((file, index) => (
        <div key={file.id || file.path} ref={(el) => (slideRefs.current[index] = el)} data-index={index}>
          <MediaSlide 
            file={file}
            index={index}
            currentIndex={currentIndex}
            // showFullSize prop removed
            onLike={() => onLike(file.id)}
            onDelete={() => onDelete(file.id)}
            showControls={true}
            zoomLevel={zoomLevel || 2.5} 
          />
        </div>
      ))}
    </div>
  );
};

export default Viewer;