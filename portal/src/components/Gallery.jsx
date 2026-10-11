import React from 'react';
import LazyImage from './LazyImage';
import Masonry from 'react-masonry-css';

const Gallery = ({ files, onImageClick, lastImageRef }) => {

  if (!files || files.length === 0) {
    return <p>No media found. Check your filters or wait for the scan to complete.</p>;
  }

  const breakpointColumnsObj = {
    default: 5,
    1400: 4,
    1024: 3,
    768: 2
  };

  return (
    <Masonry
      breakpointCols={breakpointColumnsObj}
      className="gallery-masonry-grid"
      columnClassName="gallery-masonry-column"
    >
      {files.map((file, index) => {
        const isLastElement = index === files.length - 1;
        return (
          <div
            ref={isLastElement ? lastImageRef : null}
            key={file.path + index}
            className="gallery-item"
            onClick={() => onImageClick(index)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onImageClick(index);
              }
            }}
            tabIndex={0}
            role="button"
            aria-label={`View ${file.type}${file.filename ? `: ${file.filename}` : ''}`}
          >
            <LazyImage
              src={`/api/thumbnails/${file.id}`}
              alt={file.path}
              width={file.width}
              height={file.height}
            />
            {file.type === 'video' && <div className="media-type-overlay">▶</div>}
            {file.type === 'audio' && <div className="media-type-overlay">🎵</div>}
            <div className="image-dimension-overlay">
              {file.type === 'audio' ? file.filename : (file.width > 0 ? `${file.width} x ${file.height}` : 'Video')}
            </div>
          </div>
        );
      })}
    </Masonry>
  );
};

export default Gallery;