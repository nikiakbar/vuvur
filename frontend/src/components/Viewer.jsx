import React, { useState, useEffect, useRef } from 'react';
import MediaSlide from './MediaSlide';

const ExifDisplay = ({ data, onClose }) => (
  <div className="exif-overlay" onClick={onClose}>
    <div className="exif-content" onClick={(e) => e.stopPropagation()}>
      <h3>Image Metadata (EXIF)</h3>
      <button className="exif-close-button" onClick={onClose}>&times;</button>
      <div className="exif-table">
        {Object.entries(data).map(([key, value]) => {
          const renderValue = () => {
            if ((key === 'UserComment' || key === 'parameters') && typeof value === 'string') {
              const tags = value.split(',').map(tag => tag.trim()).filter(Boolean);
              return (<div className="tag-container">{tags.map((tag, index) => <span key={index} className="tag-badge">{tag}</span>)}</div>);
            }
            return String(value);
          };
          return (<div key={key} className="exif-row"><div className="exif-key">{key}</div><div className="exif-value">{renderValue()}</div></div>)
        })}
      </div>
    </div>
  </div>
);

const Viewer = ({ files, currentIndex, onClose, onLike, onDelete, showFullSize, setCurrentIndex }) => {
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);
  const [showExif, setShowExif] = useState(false);
  
  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose() };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => { slideRefs.current[currentIndex]?.scrollIntoView({ block: 'center' }) }, []);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = parseInt(entry.target.dataset.index, 10);
          if (!isNaN(index)) {
            setCurrentIndex(index);
            setShowExif(false);
          }
        }
      });
    }, { root: scrollContainerRef.current, threshold: 0.7 });
    const refs = slideRefs.current;
    refs.forEach((ref) => { if (ref) observer.observe(ref) });
    return () => { refs.forEach((ref) => { if (ref) observer.unobserve(ref) }) };
  }, [files, setCurrentIndex]);
  
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
          />
        </div>
      ))}
    </div>
  );
};

export default Viewer;