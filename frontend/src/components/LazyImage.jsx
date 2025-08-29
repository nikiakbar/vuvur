import React, { useState, useEffect, useRef } from 'react';

const LazyImage = ({ src, alt }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const imgRef = useRef(null);

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

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    // Cleanup observer on component unmount
    return () => {
      if (imgRef.current) {
        observer.unobserve(imgRef.current);
      }
    };
  }, []);

  return (
    <img
      ref={imgRef}
      src={isLoaded ? src : ''} // Use the real src only when loaded
      alt={alt}
      className={`lazy-image ${isLoaded ? 'loaded' : ''}`}
    />
  );
};

export default LazyImage;