import React, { useState } from 'react';

const LazyImage = React.memo(({ src, alt, width, height }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const aspectRatio = width > 0 && height > 0 ? `${width} / ${height}` : '1 / 1';

  return (
    <div
      className="lazy-image-placeholder"
      style={{ aspectRatio }}
    >
      <img
        src={src}
        alt={alt}
        className={`lazy-image ${isLoaded ? 'loaded' : ''}`}
        loading="lazy"
        decoding="async"
        onLoad={() => setIsLoaded(true)}
      />
    </div>
  );
});

LazyImage.displayName = 'LazyImage';

export default LazyImage;