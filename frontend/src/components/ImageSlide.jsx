import React, { useState } from 'react';

const ImageSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, showControls }) => {
  const [isZoomed, setIsZoomed] = useState(false);

  // Determine which image source to use
  let imageUrl;
  if (showFullSize) {
    imageUrl = `/api/view/all/${encodeURIComponent(file.path)}`;
  } else {
    // Use the higher quality preview for the viewer, not the tiny thumbnail
    imageUrl = `/api/preview/${encodeURIComponent(file.path)}`;
  }

  const handleImageClick = (e) => {
    // Prevent the click from bubbling up to other elements
    e.stopPropagation();
    setIsZoomed(prev => !prev);
  };

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''}`}
        onClick={handleImageClick}
      >
        <img src={imageUrl} alt={file.path} />
      </div>

      {/* Show controls only for the currently active slide in the main viewer */}
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