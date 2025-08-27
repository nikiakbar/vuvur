import React, { useEffect, useRef } from 'react';

const Viewer = ({ files, currentIndex, onClose, onLike, onDelete, showFullSize, setCurrentIndex }) => {
  const scrollContainerRef = useRef(null);
  const slideRefs = useRef([]);

  // On initial mount, scroll to the correct image without smooth behavior
  useEffect(() => {
    slideRefs.current[currentIndex]?.scrollIntoView({ block: 'center' });
  }, []);

  // Use Intersection Observer to update the index when user scrolls
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const index = parseInt(entry.target.dataset.index, 10);
            if (!isNaN(index)) {
              setCurrentIndex(index);
            }
          }
        });
      },
      { root: scrollContainerRef.current, threshold: 0.7 }
    );

    const refs = slideRefs.current;
    refs.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    return () => {
      refs.forEach((ref) => {
        if (ref) observer.unobserve(ref);
      });
    };
  }, [files, setCurrentIndex]);
  
  return (
    <div className="viewer-overlay" ref={scrollContainerRef}>
      <button className="close-button" onClick={onClose}>&times;</button>
      {files.map((file, index) => {
        const imageUrl = showFullSize
          ? `/api/view/all/${encodeURIComponent(file)}`
          : `/api/preview/${encodeURIComponent(file)}`;

        return (
          <div
            key={file + index}
            className="viewer-slide"
            ref={(el) => (slideRefs.current[index] = el)}
            data-index={index}
          >
            <div className="viewer-image-container">
              <img src={imageUrl} alt={file} />
            </div>
            <div className="slide-info">
                <p className="viewer-filename">{file}</p>
                <div className="viewer-controls">
                    <button title="Like" onClick={() => onLike(file)}>❤️</button>
                    <button title="Delete" onClick={() => onDelete(file)}>🗑️</button>
                </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default Viewer;