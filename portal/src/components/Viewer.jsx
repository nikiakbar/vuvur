import React, { useState, useEffect, useRef } from 'react';
import MediaSlide from './MediaSlide';
import ExifDisplay from './ExifDisplay';

const Viewer = ({ files, currentIndex, onClose, onLike, onDelete, showFullSize, setCurrentIndex, zoomLevel }) => {
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);
  
  // Use a single state for EXIF data. If it's null, the component is hidden.
  const [exifData, setExifData] = useState(null);
  
  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose() };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // This effect scrolls to the initially opened image. It only runs once.
  useEffect(() => {
    slideRefs.current[currentIndex]?.scrollIntoView({ block: 'center' });
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = parseInt(entry.target.dataset.index, 10);
          if (!isNaN(index)) {
            setCurrentIndex(index);
            // When scrolling to a new slide, always hide the EXIF display.
            setExifData(null);
          }
        }
      });
    }, { root: scrollContainerRef.current, threshold: 0.7 });

    const refs = slideRefs.current;
    refs.forEach((ref) => { if (ref) observer.observe(ref) });
    return () => { refs.forEach((ref) => { if (ref) observer.unobserve(ref) }) };
  }, [files, setCurrentIndex]);
  
  const handleShowExif = (file) => {
    // This function now exclusively sets the data to be displayed.
    if (file && file.type === 'image' && file.exif) {
      try {
        setExifData(JSON.parse(file.exif));
      } catch (e) {
        console.error("Failed to parse EXIF JSON:", e);
        setExifData({ error: "Could not parse EXIF data." });
      }
    } else {
      setExifData({ error: "No EXIF data found." });
    }
  };
  
  const currentFile = files[currentIndex];
  if (!currentFile) return null;

  return (
    <div className="viewer-overlay" ref={scrollContainerRef}>
      <button className="close-button" onClick={onClose}>&times;</button>
      
      {/* The ExifDisplay is now rendered conditionally based on exifData state */}
      {exifData && (
        <ExifDisplay 
          data={exifData} 
          onClose={() => setExifData(null)} 
        />
      )}

      {files.map((file, index) => (
        <div key={file.path + index} ref={(el) => (slideRefs.current[index] = el)} data-index={index}>
          <MediaSlide 
            file={file}
            index={index}
            currentIndex={currentIndex}
            showFullSize={showFullSize}
            onLike={onLike}
            onDelete={onDelete}
            // The onClick handler is now simpler and more direct.
            onShowExif={() => handleShowExif(file)}
            showControls={true}
            zoomLevel={zoomLevel || 2.5} 
          />
        </div>
      ))}
    </div>
  );
};

export default Viewer;