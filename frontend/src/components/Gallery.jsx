import React from 'react';

const Gallery = ({ files, onImageClick, lastImageRef }) => {
  if (!files || files.length === 0) {
    return <p>No media found. Check your mounted directories.</p>;
  }
  return (
    <div className="gallery-masonry-container">
      {files.map((file, index) => {
        const isLastElement = index === files.length - 1;
        return (
          <div
            ref={isLastElement ? lastImageRef : null}
            key={file.path + index}
            className="gallery-item"
            onClick={() => onImageClick(index)}
          >
            <img src={`/api/thumbnail/${encodeURIComponent(file.path)}`} alt={file.path} loading="lazy" />
            {file.type === 'video' && <div className="media-type-overlay">▶</div>}
            <div className="image-dimension-overlay">
              {file.width > 0 ? `${file.width} x ${file.height}` : 'Video'}
            </div>
          </div>
        );
      })}
    </div>
  );
};
export default Gallery; 