import React, { useState } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);

  const mediaUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  const toggleZoom = (e) => {
    // Prevent a click on the image from triggering anything behind it
    e.stopPropagation(); 
    if (file.type === 'image') {
      setIsZoomed(prev => !prev);
    }
  };

  // For videos, we don't want the zoom click. 
  // We attach the click handler only to the container.
  const handleContainerClick = (e) => {
    if (file.type === 'image') {
      toggleZoom(e);
    }
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''}`}
        onClick={handleContainerClick}
      >
        {file.type === 'image' ? (
          <img 
            src={mediaUrl} 
            alt={file.path} 
            style={{ 
              transform: `scale(${isZoomed ? zoomLevel : 1})`,
              pointerEvents: isZoomed ? 'auto' : 'none' // Let img be interactive when zoomed
            }}
          />
        ) : (
          <video 
            src={mediaUrl} 
            controls 
            autoPlay 
            muted 
            loop 
            onClick={(e) => e.stopPropagation()} // Stop video click from zooming out
          />
        )}
      </div>

      {showControls && index === currentIndex && (
        <div className="slide-info">
            <p className="viewer-filename">{file.path}</p>
            <div className="viewer-controls">
                {file.type === 'image' && <button title="Show EXIF" onClick={onShowExif}>ℹ️</button>}
                <button title="Like" onClick={() => onLike(file.path)}>❤️</button>
                <button title="Delete" onClick={() => onDelete(file.path)}>🗑️</button>
            </div>
        </div>
      )}
    </div>
  );
};

export default MediaSlide;