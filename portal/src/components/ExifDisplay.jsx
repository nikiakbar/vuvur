import React from 'react';

// This is the standalone ExifDisplay component
const ExifDisplay = ({ data, onClose }) => {
  const renderValue = (key, value) => {
    // Check for the special keys that contain AI-generated tags
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
    // Render all other values normally
    return String(value);
  };

  return (
    <div className="exif-overlay" onClick={onClose}>
      <div className="exif-content" onClick={(e) => e.stopPropagation()}>
        <h3>Image Metadata (EXIF)</h3>
        <button className="exif-close-button" onClick={onClose}>&times;</button>
        <div className="exif-table">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="exif-row">
              <div className="exif-key">{key}</div>
              <div className="exif-value">{renderValue(key, value)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ExifDisplay;