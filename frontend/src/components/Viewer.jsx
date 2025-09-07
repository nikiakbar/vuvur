import React, { useState, useEffect, useRef } from 'react';
import MediaSlide from './MediaSlide'; 

const ExifDisplay = ({ data, onClose }) => (
  // ... (This sub-component remains unchanged)
  <div className="exif-overlay" onClick={onClose}>{/*...*/}</div>
);

// Receive zoomLevel as a prop
const Viewer = ({ files, currentIndex, onClose, onLike, onDelete, showFullSize, setCurrentIndex, zoomLevel }) => {
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);
  const [showExif, setShowExif] = useState(false);
  
  // ... (all hooks remain unchanged) ...
  useEffect(() => { /* ... (Esc key) ... */ }, [onClose]);
  useEffect(() => { /* ... (scroll to index on mount) ... */ }, []);
  useEffect(() => { /* ... (IntersectionObserver) ... */ }, [files, setCurrentIndex]);
  
  const currentFile = files[currentIndex];
  if (!currentFile) return null;

  const handleShowExif = () => {
    if (currentFile.type === 'image') {
      setShowExif(true);
    }
  };

  return (
    <div className="viewer-overlay" ref={scrollContainerRef}>
      <button className="close-button" onClick={onClose}>&times;</button>
      
      {showExif && (
        <ExifDisplay 
          data={currentFile.exif || { error: "No EXIF data found." }} 
          onClose={() => setShowExif(false)} 
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
            onShowExif={handleShowExif}
            showControls={true}
            zoomLevel={zoomLevel} /* Pass the prop down */
          />
        </div>
      ))}
    </div>
  );
};

export default Viewer;