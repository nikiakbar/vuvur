import React, { useState } from 'react';

const MediaSlide = ({ file, index, currentIndex, showFullSize, onLike, onDelete, showControls, onShowExif }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  // Panning state is omitted for brevity but would be added here

  const handleImageClick = (e) => {
    e.stopPropagation();
    if (file.type === 'image') { // Only allow zoom for images
      setIsZoomed(prev => !prev);
    }
  };
  
  const mediaUrl = showFullSize 
    ? `/api/view/all/${encodeURIComponent(file.path)}`
    : `/api/preview/${encodeURIComponent(file.path)}`;

  return (
    <div className="viewer-slide">
      <div 
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''}`}
        onClick={handleImageClick}
      >
        {file.type === 'image' ? (
          <img src={mediaUrl} alt={file.path} />
        ) : (
          <video src={mediaUrl} controls autoPlay muted loop />
        )}
      </div>

      {showControls && index === currentIndex && (
        <div className="slide-info">
            <p className="viewer-filename">{file.path}</p>
            <div className="viewer-controls">
                {file.type === 'image' && <button title="Show EXIF" onClick={() => onShowExif(file.path)}>ℹ️</button>}
                <button title="Like" onClick={() => onLike(file.path, file.type)}>❤️</button>
                <button title="Delete" onClick={() => onDelete(file.path, file.type)}>🗑️</button>
            </div>
        </div>
      )}
    </div>
  );
};

export default MediaSlide;