import React, { useState, useRef } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentPan, setCurrentPan] = useState({ x: 0, y: 0 });
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });
  const [didDrag, setDidDrag] = useState(false);
  
  const DRAG_THRESHOLD = 30; // Pixel "dead zone"

  const mediaUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  const handlePointerDown = (clientX, clientY) => {
    setDidDrag(false); // Reset drag status on every new touch/click
    setIsDragging(true);
    setStartPos({ x: clientX, y: clientY });
    setStartPan(currentPan); // Store the pan offset at the start
  };

  const handlePointerMove = (clientX, clientY, event) => {
    if (!isDragging) return;

    const deltaX = clientX - startPos.x;
    const deltaY = clientY - startPos.y;

    if (!didDrag && (Math.abs(deltaX) > DRAG_THRESHOLD || Math.abs(deltaY) > DRAG_THRESHOLD)) {
      setDidDrag(true);
    }

    // Only pan if we are zoomed in AND this is an image
    if (isZoomed && file.type === 'image') {
      // If we are zoomed, we are panning. Prevent the whole page from scrolling.
      if (event) {
        event.preventDefault();
      }
      setCurrentPan({
        x: startPan.x + deltaX,
        y: startPan.y + deltaY
      });
    }
    // If NOT zoomed, we let the default swipe action (page scroll) happen.
    // The didDrag flag is set, so it won't trigger a zoom on pointer up.
  };

  const handlePointerUp = () => {
    if (!didDrag) {
      if (file.type === 'image') { // Only zoom on images
        const newZoomState = !isZoomed;
        setIsZoomed(newZoomState);
        if (!newZoomState) {
          setCurrentPan({ x: 0, y: 0 }); // Reset pan on zoom out
        }
      }
    }
    setIsDragging(false);
  };

  // --- Mouse Event Handlers ---
  const handleMouseDown = (e) => {
    e.preventDefault();
    handlePointerDown(e.clientX, e.clientY);
  };

  const handleMouseMove = (e) => {
    e.preventDefault();
    handlePointerMove(e.clientX, e.clientY, null);
  };

  // --- Touch Event Handlers ---
  const handleTouchStart = (e) => {
    if (e.touches.length !== 1) {
      setIsDragging(false);
      return;
    }
    handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
  };

  const handleTouchMove = (e) => {
    if (e.touches.length !== 1) return;
    // We pass the native 'e' event so we can call e.preventDefault() inside the handler
    handlePointerMove(e.touches[0].clientX, e.touches[0].clientY, e);
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''} ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handlePointerUp}
        onMouseLeave={handlePointerUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handlePointerUp}
        onTouchCancel={handlePointerUp}
      >
        {file.type === 'image' ? (
          <img 
            src={mediaUrl} 
            alt={file.path} 
            style={{ 
              transform: `scale(${isZoomed ? zoomLevel : 1}) translate(${currentPan.x}px, ${currentPan.y}px)`,
              pointerEvents: 'none'
            }}
          />
        ) : (
          <video src={mediaUrl} controls autoPlay muted loop />
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