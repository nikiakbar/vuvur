import React, { useState, useEffect, useRef } from 'react';

// This sub-component now has special logic for rendering tags
const ExifDisplay = ({ data, onClose }) => {
  const renderValue = (key, value) => {
    // Check for the special keys that contain AI-generated tags
    if ((key === 'UserComment' || key === 'parameters') && typeof value === 'string') {
      const tags = value.split(',').map(tag => tag.trim()).filter(Boolean);
      return (
        <div className="tag-container">
          {tags.map((tag, index) => (
            <span key={index} className="tag-badge">{tag}</span>
          ))}
        </div>
      );
    }
    // Render all other values normally
    return String(value);
  };

  return (
    <div className="exif-overlay" onClick={onClose}>
      <div className="exif-content" onClick={(e) => e.stopPropagation()}>
        <h3>Image Metadata (EXIF)</h3>
        <button className="exif-close-button" onClick={onClose}>&times;</button>
        <div className="exif-table">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="exif-row">
              <div className="exif-key">{key}</div>
              <div className="exif-value">{renderValue(key, value)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};


const Viewer = ({ files, currentIndex, onClose, onLike, onDelete, showFullSize, setCurrentIndex }) => {
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);
  
  const [exifData, setExifData] = useState(null);
  const [showExif, setShowExif] = useState(false);
  const [isLoadingExif, setIsLoadingExif] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose() };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    slideRefs.current[currentIndex]?.scrollIntoView({ block: 'center' });
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const index = parseInt(entry.target.dataset.index, 10);
            if (!isNaN(index)) {
              setCurrentIndex(index);
              setShowExif(false);
              setExifData(null);
            }
          }
        });
      },
      { root: scrollContainerRef.current, threshold: 0.7 }
    );
    const refs = slideRefs.current;
    refs.forEach((ref) => { if (ref) observer.observe(ref) });
    return () => { refs.forEach((ref) => { if (ref) observer.unobserve(ref) }) };
  }, [files, setCurrentIndex]);
  
  const currentFile = files[currentIndex];
  if (!currentFile) return null;

  const handleShowExif = async () => {
    if (showExif) {
      setShowExif(false);
      return;
    }

    setShowExif(true);
    if (exifData) return;

    setIsLoadingExif(true);
    try {
      const response = await fetch(`/api/exif/${encodeURIComponent(currentFile.path)}`);
      const data = await response.json();
      setExifData(data);
    } catch (error) {
      setExifData({ error: "Could not load metadata." });
    } finally {
      setIsLoadingExif(false);
    }
  };

  return (
    <div className="viewer-overlay" ref={scrollContainerRef}>
      <button className="close-button" onClick={onClose}>&times;</button>
      
      {showExif && (
        <ExifDisplay 
          data={isLoadingExif ? { status: "Loading..." } : exifData} 
          onClose={() => setShowExif(false)} 
        />
      )}

      {files.map((file, index) => {
        const itemImageUrl = showFullSize
          ? `/api/view/all/${encodeURIComponent(file.path)}`
          : `/api/preview/${encodeURIComponent(file.path)}`;

        return (
          <div
            key={file.path + index}
            className="viewer-slide"
            ref={(el) => (slideRefs.current[index] = el)}
            data-index={index}
          >
            <div className="viewer-image-container">
              <img src={itemImageUrl} alt={file.path} />
            </div>
            {index === currentIndex && (
              <div className="slide-info">
                  <p className="viewer-filename">{file.path}</p>
                  <div className="viewer-controls">
                      <button title="Show EXIF" onClick={handleShowExif}>ℹ️</button>
                      <button title="Like" onClick={() => onLike(file.path)}>❤️</button>
                      <button title="Delete" onClick={() => onDelete(file.path)}>🗑️</button>
                  </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default Viewer;