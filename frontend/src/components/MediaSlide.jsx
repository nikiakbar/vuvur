import React, { useState, useRef } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const containerRef = useRef(null);

  const mediaUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  const toggleZoom = (e) => {
    e.stopPropagation(); 
    if (file.type !== 'image') {
      return;
    }

    const newZoomState = !isZoomed;
    setIsZoomed(newZoomState);

    if (newZoomState) {
      // This is the fix:
      // After React renders the 'zoomed' class, push this task to the event queue.
      // This gives the browser time to calculate the new scroll dimensions.
      setTimeout(() => {
        if (containerRef.current) {
          const container = containerRef.current;
          // Calculate the new center scroll position
          const scrollWidth = container.scrollWidth - container.clientWidth;
          const scrollHeight = container.scrollHeight - container.clientHeight;
          // Set the scrollbars to the middle
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

  return (
    <div className="viewer-slide">
      <div 
        ref={containerRef}
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''}`}
        onClick={handleContainerClick}
      >
        {file.type === 'image' ? (
          <img 
            src={mediaUrl} 
            alt={file.path} 
            style={{ 
              transform: `scale(${isZoomed ? zoomLevel : 1})`,
              pointerEvents: isZoomed ? 'auto' : 'none'
            }}
          />
        ) : (
          <video 
            src={mediaUrl} 
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