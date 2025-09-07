import React, { useState, useEffect, useRef } from 'react';

const LazyImage = ({ src, alt, width, height }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const placeholderRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          // When the image placeholder is visible, start loading the real image
          if (entry.isIntersecting) {
            setIsLoaded(true);
            observer.unobserve(entry.target); // Stop observing once loaded
          }
        });
      },
      // Start loading when the image is 200px away from the viewport
      { rootMargin: '200px' } 
    );

    if (placeholderRef.current) {
      observer.observe(placeholderRef.current);
    }

    // Cleanup observer on component unmount
    return () => {
      if (placeholderRef.current) {
        // eslint-disable-next-line react-hooks/exhaustive-deps
        observer.unobserve(placeholderRef.current);
      }
    };
  }, []);

  // Calculate aspect ratio only if dimensions are valid
  const aspectRatio = width > 0 && height > 0 ? `${width} / ${height}` : '1 / 1';

  return (
    <div
      ref={placeholderRef}
      className="lazy-image-placeholder"
      style={{ aspectRatio }}
    >
      {isLoaded && (
        <img
          src={src}
          alt={alt}
          className="lazy-image loaded"
        />
      )}
    </div>
  );
};

export default LazyImage;