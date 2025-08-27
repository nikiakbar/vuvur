import React from 'react';

const Gallery = ({ files, onImageClick }) => {
  if (!files || files.length === 0) {
    return <p>No media files found. Add some images to the backend/media/all directory.</p>;
  }

  return (
    <div className="gallery-grid">
      {files.map((file, index) => (
        <div 
          key={file + index} // Add index to key for when shuffle returns same files
          className="gallery-item" 
          onClick={() => onImageClick(index)}
        >
          <img src={`/api/preview/${encodeURIComponent(file)}`} alt={file} loading="lazy" />
        </div>
      ))}
    </div>
  );
};

export default Gallery;