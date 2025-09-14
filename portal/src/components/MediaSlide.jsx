import React, { useState, useRef, useEffect } from 'react';

// A simple component to render the EXIF data table, now used internally
const ExifTable = ({ data }) => {
  const renderValue = (key, value) => {
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
    return String(value);
  };

  return (
    <div className="exif-table-embedded">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="exif-row">
          <div className="exif-key">{key}</div>
          <div className="exif-value">{renderValue(key, value)}</div>
        </div>
      ))}
    </div>
  );
};


const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentPan, setCurrentPan] = useState({ x: 0, y: 0 });
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });
  const didDrag = useRef(false);
  const videoRef = useRef(null);
  const slideInfoRef = useRef(null);
  const DRAG_THRESHOLD = 10;
  
  // State to toggle EXIF visibility
  const [showExif, setShowExif] = useState(false);

  useEffect(() => {
    if (videoRef.current) {
      if (index === currentIndex) {
        videoRef.current.play().catch(error => {});
      } else {
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      }
    }
    // Reset EXIF view when scrolling to a new slide
    if (index !== currentIndex) {
      setShowExif(false);
    }
  }, [currentIndex, index]);

  const imageUrl = showFullSize ? `/api/stream/${file.id}` : `/api/preview/${file.id}`;
  const videoUrl = `/api/stream/${file.id}`;

  const handlePointerDown = (clientX, clientY) => {
    didDrag.current = false;
    setIsDragging(true);
    setStartPos({ x: clientX, y: clientY });
    setStartPan(currentPan);
  };

  const handlePointerMove = (clientX, clientY, event) => {
    if (!isDragging) return;
    if (event) event.preventDefault();
    const deltaX = clientX - startPos.x;
    const deltaY = clientY - startPos.y;
    if (!didDrag.current && (Math.abs(deltaX) > DRAG_THRESHOLD || Math.abs(deltaY) > DRAG_THRESHOLD)) {
      didDrag.current = true;
    }
    if (isZoomed && file.type === 'image') {
      setCurrentPan({ x: startPan.x + deltaX, y: startPan.y + deltaY });
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

  const handleShowExif = (e) => {
    e.stopPropagation();
    setShowExif(!showExif); // Toggle visibility
  };

  const handleLikeClick = (e) => {
    e.stopPropagation();
    onLike();
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete();
  };

  const handleMouseDown = (e) => {
    if (slideInfoRef.current && slideInfoRef.current.contains(e.target)) return;
    handlePointerDown(e.clientX, e.clientY);
  };

  const handleTouchStart = (e) => {
    if (slideInfoRef.current && slideInfoRef.current.contains(e.target)) return;
    if (e.touches.length === 1) handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
  };

  const getExifData = () => {
    if (file && file.type === 'image' && file.exif) {
      try { return JSON.parse(file.exif); } 
      catch (e) { return { error: 'Could not parse EXIF data.' }; }
    }
    return { error: 'No EXIF data found.' };
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={(e) => handlePointerMove(e.clientX, e.clientY, e)}
        onMouseUp={handlePointerUp}
        onMouseLeave={() => setIsDragging(false)}
        onTouchStart={handleTouchStart}
        onTouchMove={(e) => e.touches.length === 1 && handlePointerMove(e.touches[0].clientX, e.touches[0].clientY, e)}
        onTouchEnd={handlePointerUp}
        onTouchCancel={() => setIsDragging(false)}
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
            ref={videoRef}
            src={videoUrl} 
            controls 
            loop 
            onClick={(e) => e.stopPropagation()} 
          />
        )}
      </div>

      {showControls && index === currentIndex && (
        <div className={`slide-info ${showExif ? 'expanded' : ''}`} ref={slideInfoRef}>
          {showExif ? (
            <ExifTable data={getExifData()} />
          ) : (
            <p className="viewer-filename">{file.path}</p>
          )}
          <div className="viewer-controls">
            {file.type === 'image' && <button title="Show EXIF" onClick={handleShowExif}>ℹ️</button>}
            <button title="Like" onClick={handleLikeClick}>❤️</button>
            <button title="Delete" onClick={handleDeleteClick}>🗑️</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MediaSlide;