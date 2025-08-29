import React, { useState, useRef } from 'react';

const ImageSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, showControls }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [didDrag, setDidDrag] = useState(false);
  
  const imageRef = useRef(null);

  const imageUrl = showFullSize
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  const handleMouseDown = (e) => {
    if (!isZoomed) return;
    e.preventDefault();
    setIsDragging(true);
    setStartPos({ 
      x: e.clientX - panOffset.x,
      y: e.clientY - panOffset.y 
    });
    setDidDrag(false); // Reset drag flag on new mousedown
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setDidDrag(true); // Flag that a drag has occurred
    setPanOffset({
      x: e.clientX - startPos.x,
      y: e.clientY - startPos.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    // If we didn't drag, treat it as a click to zoom out
    if (!didDrag && isZoomed) {
      setIsZoomed(false);
      setPanOffset({ x: 0, y: 0 });
    }
  };
  
  const handleMouseLeave = () => {
    setIsDragging(false);
  };
  
  const handleImageClick = (e) => {
    e.stopPropagation();
    // Only toggle zoom on click if not already zoomed
    if (!isZoomed) {
      setIsZoomed(true);
    }
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''} ${isDragging ? 'dragging' : ''}`}
        onClick={handleImageClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      >
        <img 
          ref={imageRef}
          src={imageUrl} 
          alt={file.path} 
          style={{ 
            transform: `scale(${isZoomed ? 2.5 : 1}) translate(${panOffset.x}px, ${panOffset.y}px)`
          }}
        />
      </div>

      {showControls && index === currentIndex && (
        <div className="slide-info">
            <p className="viewer-filename">{file.path}</p>
            <div className="viewer-controls">
                <button title="Show EXIF" onClick={() => onLike(file.path)}>ℹ️</button>
                <button title="Like" onClick={() => onLike(file.path)}>❤️</button>
                <button title="Delete" onClick={() => onDelete(file.path)}>🗑️</button>
            </div>
        </div>
      )}
    </div>
  );
};

export default ImageSlide;