import React from 'react';

const Gallery = ({ files, onImageClick, lastImageRef }) => {

  if (!files || files.length === 0) {
    return <p>No media files found. Add some images to the backend/media/all directory.</p>;
  }

  return (
    <div className="gallery-masonry-container">
      {files.map((file, index) => {
        const isLastElement = index === files.length - 1;
        return (
          <div
            // If this is the last element, attach the ref to it
            ref={isLastElement ? lastImageRef : null}
            key={file.path + index}
            className="gallery-item"
            onClick={() => onImageClick(index)}
          >
            <img src={`/api/thumbnail/${encodeURIComponent(file.path)}`} alt={file.path} loading="lazy" />
            <div className="image-dimension-overlay">
              {file.width} x {file.height}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default Gallery;