import React, { useState } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [didDrag, setDidDrag] = useState(false);

  const mediaUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  // --- Unified Event Logic ---

  const handlePointerDown = (clientX, clientY) => {
    if (!isZoomed || file.type !== 'image') {
      // If not zoomed, set didDrag to false so the "up" event will trigger zoom
      setDidDrag(false);
      return;
    }
    // If we are zoomed, prepare to pan
    setIsDragging(true);
    setStartPos({ 
      x: clientX - panOffset.x,
      y: clientY - panOffset.y 
    });
    setDidDrag(false);
  };

  const handlePointerMove = (clientX, clientY) => {
    if (!isZoomed || !isDragging) return;
    setDidDrag(true); // Flag that a drag has occurred
    setPanOffset({
      x: clientX - startPos.x,
      y: clientY - startPos.y
    });
  };

  const handlePointerUp = () => {
    setIsDragging(false);
    // If we didn't drag, it was a click/tap. Toggle zoom.
    if (!didDrag) {
      const newZoomState = !isZoomed;
      setIsZoomed(newZoomState);
      if (!newZoomState) {
        // If we just zoomed out, reset the pan
        setPanOffset({ x: 0, y: 0 });
      }
    }
  };

  // --- Mouse Event Handlers ---
  const handleMouseDown = (e) => {
    e.preventDefault(); // Prevent default image drag
    handlePointerDown(e.clientX, e.clientY);
  };

  const handleMouseMove = (e) => {
    handlePointerMove(e.clientX, e.clientY);
  };

  // --- Touch Event Handlers ---
  const handleTouchStart = (e) => {
    if (e.touches.length !== 1) return; // Only pan with one finger
    handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
  };

  const handleTouchMove = (e) => {
    if (e.touches.length !== 1) return;
    handlePointerMove(e.touches[0].clientX, e.touches[0].clientY);
  };

  // onMouseLeave handles if the user drags off-screen
  const handleMouseLeave = () => {
    if (isDragging) {
      handlePointerUp();
    }
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''} ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handlePointerUp}
        onMouseLeave={handleMouseLeave}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handlePointerUp}
      >
        {file.type === 'image' ? (
          <img 
            src={mediaUrl} 
            alt={file.path} 
            style={{ 
              transform: `scale(${isZoomed ? zoomLevel : 1}) translate(${panOffset.x}px, ${panOffset.y}px)`,
              pointerEvents: isZoomed ? 'none' : 'auto' // Prevent image ghost-drag
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