import React, { useState, useRef, useEffect } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentPan, setCurrentPan] = useState({ x: 0, y: 0 });
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });
  const didDrag = useRef(false);
  const videoRef = useRef(null); // Create a ref for the video element
  const DRAG_THRESHOLD = 10;

  // This effect will pause videos that are not in view
  useEffect(() => {
    if (videoRef.current) {
      if (index === currentIndex) {
        // Autoplay the current video
        videoRef.current.play().catch(error => {
          // Autoplay was prevented, which is common in browsers.
          // The user will have to click the play button manually.
        });
      } else {
        // Pause and reset any video that is not the current one
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      }
    }
  }, [currentIndex, index]);

  const imageUrl = showFullSize 
    ? `/api/stream/${file.id}`
    : `/api/preview/${file.id}`;
  const videoUrl = `/api/stream/${file.id}`;

  const handlePointerDown = (clientX, clientY) => {
    didDrag.current = false;
    setIsDragging(true);
    setStartPos({ x: clientX, y: clientY });
    setStartPan(currentPan);
  };

  const handlePointerMove = (clientX, clientY, event) => {
    if (!isDragging) return;
    const deltaX = clientX - startPos.x;
    const deltaY = clientY - startPos.y;
    if (!didDrag.current && (Math.abs(deltaX) > DRAG_THRESHOLD || Math.abs(deltaY) > DRAG_THRESHOLD)) {
      didDrag.current = true;
    }
    if (isZoomed && file.type === 'image') {
      if (event) event.preventDefault();
      setCurrentPan({
        x: startPan.x + deltaX,
        y: startPan.y + deltaY
      });
    }
  };

  const handlePointerUp = () => {
    if (!didDrag.current && file.type === 'image') {
      const newZoomState = !isZoomed;
      setIsZoomed(newZoomState);
      if (!newZoomState) {
        setCurrentPan({ x: 0, y: 0 });
      }
    }
    setIsDragging(false);
    setTimeout(() => { didDrag.current = false; }, 0);
  };

  const handleMouseDown = (e) => { e.preventDefault(); handlePointerDown(e.clientX, e.clientY); };
  const handleMouseMove = (e) => { e.preventDefault(); handlePointerMove(e.clientX, e.clientY, e); };
  const handleTouchStart = (e) => {
    if (e.touches.length !== 1) { setIsDragging(false); return; }
    handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
  };
  const handleTouchMove = (e) => {
    if (!isDragging || e.touches.length !== 1) return;
    handlePointerMove(e.touches[0].clientX, e.touches[0].clientY, e);
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''} ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handlePointerUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handlePointerUp}
        onTouchCancel={handlePointerUp}
      >
        {file.type === 'image' ? (
          <img 
            src={imageUrl} 
            alt={file.path} 
            style={{ 
              transform: `scale(${isZoomed ? zoomLevel : 1}) translate(${currentPan.x}px, ${currentPan.y}px)`,
              pointerEvents: 'none'
            }}
          />
        ) : (
          <video 
            ref={videoRef} // Attach the ref to the video element
            src={videoUrl} 
            controls 
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