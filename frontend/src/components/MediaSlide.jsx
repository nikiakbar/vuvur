import React, { useState, useRef } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const containerRef = useRef(null);

  const toggleZoom = (e) => {
    e.stopPropagation(); 
    if (file.type !== 'image') {
      return;
    }

    const newZoomState = !isZoomed;
    setIsZoomed(newZoomState);

    if (newZoomState) {
      setTimeout(() => {
        if (containerRef.current) {
          const container = containerRef.current;
          const scrollWidth = container.scrollWidth - container.clientWidth;
          const scrollHeight = container.scrollHeight - container.clientHeight;
          container.scrollLeft = scrollWidth / 2;
          container.scrollTop = scrollHeight / 2;
        }
      }, 0);
    }
  };

  const handleContainerClick = (e) => {
    if (file.type === 'image') {
      toggleZoom(e);
    }
  };

  // Create two separate URL paths
  const imageUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;
    
  // Videos MUST always use the full 'view' endpoint to be playable
  const videoUrl = `/api/view/all/${encodeURIComponent(file.path)}`;

  return (
    <div className="viewer-slide">
      <div 
        ref={containerRef} 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''}`}
        onClick={handleContainerClick}
      >
        {file.type === 'image' ? (
          <img 
            src={imageUrl} 
            alt={file.path} 
            style={{ 
              transform: `scale(${isZoomed ? zoomLevel : 1})`,
              pointerEvents: isZoomed ? 'auto' : 'none'
            }}
          />
        ) : (
          <video 
            src={videoUrl} 
            controls 
            autoPlay 
            muted 
            loop 
            onClick={(e) => e.stopPropagation()} 
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