import React, { useState } from 'react';

// Receive zoomLevel as a prop
const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, onShowExif, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [didDrag, setDidDrag] = useState(false);

  const mediaUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  const handleMouseDown = (e) => {
    if (!isZoomed || file.type !== 'image') return;
    e.preventDefault();
    setIsDragging(true);
    setStartPos({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    setDidDrag(false);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setDidDrag(true);
    setPanOffset({ x: e.clientX - startPos.x, y: e.clientY - startPos.y });
  };

  const handleMouseUpOrLeave = () => {
    setIsDragging(false);
  };
  
  const handleClick = (e) => {
    e.stopPropagation();
    if (file.type !== 'image') return;
    if (!didDrag) {
      setIsZoomed(prev => !prev);
      if (isZoomed) {
        setPanOffset({ x: 0, y: 0 });
      }
    }
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''} ${isDragging ? 'dragging' : ''}`}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUpOrLeave}
        onMouseLeave={handleMouseUpOrLeave}
      >
        {file.type === 'image' ? (
          <img 
            src={mediaUrl} 
            alt={file.path} 
            style={{ 
              // Use the zoomLevel prop here instead of 2.5
              transform: `scale(${isZoomed ? zoomLevel : 1}) translate(${panOffset.x}px, ${panOffset.y}px)` 
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