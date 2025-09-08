import React, { useState, useRef } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentPan, setCurrentPan] = useState({ x: 0, y: 0 });
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });
  const [didDrag, setDidDrag] = useState(false);
  
  const DRAG_THRESHOLD = 30; // Increased drag sensitivity threshold

  const mediaUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  // --- Unified Event Logic ---

  const handlePointerDown = (clientX, clientY) => {
    setDidDrag(false);
    setIsDragging(true);
    // Record starting position of the cursor/finger
    setStartPos({ x: clientX, y: clientY });
    // Record the pan offset at the start of the drag
    setStartPan(currentPan);
  };

  const handlePointerMove = (clientX, clientY) => {
    if (!isDragging) return;

    const deltaX = clientX - startPos.x;
    const deltaY = clientY - startPos.y;

    // Check if the movement has exceeded the threshold
    if (!didDrag && (Math.abs(deltaX) > DRAG_THRESHOLD || Math.abs(deltaY) > DRAG_THRESHOLD)) {
      setDidDrag(true);
    }

    // Only pan the image if we are actually zoomed in and dragging
    if (isZoomed && file.type === 'image') {
      setCurrentPan({
        x: startPan.x + deltaX,
        y: startPan.y + deltaY
      });
    }
  };

  const handlePointerUp = () => {
    setIsDragging(false);
    
    // If we did not move past the drag threshold, it was a "tap" or "click".
    if (!didDrag) {
      if (file.type === 'image') { // Only zoom on images
        const newZoomState = !isZoomed;
        setIsZoomed(newZoomState);
        if (!newZoomState) {
          // If we just zoomed out, reset the pan
          setCurrentPan({ x: 0, y: 0 });
        }
      }
    }
  };

  // --- Mouse Event Handlers ---
  const handleMouseDown = (e) => {
    e.preventDefault();
    handlePointerDown(e.clientX, e.clientY);
  };

  const handleMouseMove = (e) => {
    handlePointerMove(e.clientX, e.clientY);
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
    
    // If we are zoomed, prevent the page from scrolling while we pan
    if (isZoomed && didDrag) {
      e.preventDefault();
    }
    handlePointerMove(e.touches[0].clientX, e.touches[0].clientY);
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''} ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handlePointerUp}
        onMouseLeave={handlePointerUp} // Use Up handler to stop drag
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
              pointerEvents: isZoomed ? 'none' : 'auto'
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