import React, { useState, useRef, useEffect } from 'react';
import HeartIcon from './HeartIcon';

// A simple component to render the EXIF data table, now used internally
const ExifTable = ({ data }) => {
  // Check if data is null, empty, or just contains an error message
  if (!data || Object.keys(data).length === 0 || (Object.keys(data).length === 1 && data.error)) {
    return <p className="exif-message">No EXIF data available for this image.</p>;
  }

  const renderValue = (key, value) => {
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
    return String(value);
  };

  return (
    <div className="exif-table-embedded">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="exif-row">
          <div className="exif-key">{key}</div>
          <div className="exif-value">{renderValue(key, value)}</div>
        </div>
      ))}
    </div>
  );
};


// ✅ Added onClose prop
const MediaSlide = ({ file, index, currentIndex, onLike, onDelete, onClose, showControls, zoomLevel }) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [currentPan, setCurrentPan] = useState({ x: 0, y: 0 });
  const startPosRef = useRef({ x: 0, y: 0 });
  const startPanRef = useRef({ x: 0, y: 0 });
  const didDrag = useRef(false);
  const videoRef = useRef(null);
  const slideInfoRef = useRef(null);
  const DRAG_THRESHOLD = 10;

  const [showExif, setShowExif] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(true);
  const hideTimerRef = useRef(null);

  const resetControlsVisibility = () => {
    setControlsVisible(true);
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
    }
    if (!showExif) {
      hideTimerRef.current = setTimeout(() => {
        setControlsVisible(false);
      }, 3000);
    }
  };

  useEffect(() => {
    if (index === currentIndex) {
      resetControlsVisibility();
    }
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, [index, currentIndex, showExif]);

  useEffect(() => {
    if (videoRef.current && (file.type === 'video' || file.type === 'audio')) {
      if (index === currentIndex) {
        videoRef.current.play().catch(() => { });
      } else {
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      }
    }
    if (index !== currentIndex) {
      setShowExif(false);
      setIsZoomed(false);
      setCurrentPan({ x: 0, y: 0 });
    }
  }, [currentIndex, index]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (index === currentIndex && (e.key === 'i' || e.key === 'I')) {
        if (file.type === 'image') {
          setShowExif(prev => !prev);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [index, currentIndex, file.type]);

  const imageUrl = `/api/stream/${file.id}`;
  const videoUrl = `/api/stream/${file.id}`;

  const handlePointerDown = (clientX, clientY) => {
    didDrag.current = false;
    setIsDragging(true);
    startPosRef.current = { x: clientX, y: clientY };
    startPanRef.current = currentPan;
  };

  const handlePointerMove = (clientX, clientY) => {
    const deltaX = clientX - startPosRef.current.x;
    const deltaY = clientY - startPosRef.current.y;
    if (!didDrag.current && (Math.abs(deltaX) > DRAG_THRESHOLD || Math.abs(deltaY) > DRAG_THRESHOLD)) {
      didDrag.current = true;
    }
    if (isZoomed && file.type === 'image') {
      setCurrentPan({ x: startPanRef.current.x + deltaX, y: startPanRef.current.y + deltaY });
    }
  };

  const handlePointerUp = () => {
    setIsDragging(false);
    if (!didDrag.current && file.type === 'image') {
      setIsZoomed(prev => {
        const next = !prev;
        if (!next) {
          setCurrentPan({ x: 0, y: 0 });
        }
        return next;
      });
    }
    setTimeout(() => { didDrag.current = false; }, 0);
  };

  // Global window listeners while dragging to handle mouse moving outside container
  useEffect(() => {
    if (!isDragging) return;

    const onWindowMouseMove = (e) => {
      e.preventDefault();
      handlePointerMove(e.clientX, e.clientY);
    };

    const onWindowMouseUp = () => {
      handlePointerUp();
    };

    window.addEventListener('mousemove', onWindowMouseMove);
    window.addEventListener('mouseup', onWindowMouseUp);

    return () => {
      window.removeEventListener('mousemove', onWindowMouseMove);
      window.removeEventListener('mouseup', onWindowMouseUp);
    };
  }, [isDragging, isZoomed, file.type]);

  const handleShowExif = (e) => {
    e.stopPropagation();
    setShowExif(!showExif);
  };

  const handleLikeClick = (e) => {
    e.stopPropagation();
    onLike();
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete();
  };

  // ✅ Add handler for the new close button
  const handleCloseClick = (e) => {
    e.stopPropagation();
    onClose(); // Call the passed-in onClose function
  };

  const handleInfoBarClick = (e) => {
    e.stopPropagation();
  };

  const getExifData = () => {
    if (file && file.exif && typeof file.exif === 'object' && Object.keys(file.exif).length > 0) {
      return file.exif;
    }
    if (file && file.exif && typeof file.exif === 'string' && file.exif.trim() !== '' && file.exif.trim() !== '{}') {
      try {
        const parsed = JSON.parse(file.exif);
        return Object.keys(parsed).length > 0 ? parsed : { error: 'No EXIF data found.' };
      } catch (e) {
        console.error("Could not parse EXIF string:", e);
        return { error: 'Could not parse EXIF data.' };
      }
    }
    return { error: 'No EXIF data found.' };
  };

  const exifData = React.useMemo(() => getExifData(), [file]);


  return (
    <div 
      className="viewer-slide"
      onMouseMove={resetControlsVisibility}
      onTouchStart={resetControlsVisibility}
    >
      <div
        className={`viewer-image-container ${isZoomed ? 'zoomed' : ''} ${isDragging && isZoomed ? 'dragging' : ''}`}
        onMouseDown={(e) => {
          if (e.button !== 0) return;
          if (file.type === 'image') e.preventDefault();
          handlePointerDown(e.clientX, e.clientY);
        }}
        onMouseUp={handlePointerUp}
        onTouchStart={(e) => {
          if (isZoomed) e.stopPropagation();
          if (e.touches.length === 1) handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
        }}
        onTouchMove={(e) => {
          if (isZoomed) e.stopPropagation();
          if (e.touches.length === 1) handlePointerMove(e.touches[0].clientX, e.touches[0].clientY);
        }}
        onTouchEnd={(e) => {
          if (isZoomed) e.stopPropagation();
          handlePointerUp();
        }}
        onTouchCancel={() => setIsDragging(false)}
      >
        {file.type === 'image' ? (
          <img
            src={imageUrl}
            alt={file.path}
            decoding="async"
            draggable="false"
            onDragStart={(e) => e.preventDefault()}
            style={{
              transform: `scale(${isZoomed ? zoomLevel : 1}) translate(${currentPan.x}px, ${currentPan.y}px)`,
              pointerEvents: 'none'
            }}
          />
        ) : file.type === 'audio' ? (
          <div className="audio-player-wrapper" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <h3 style={{ color: 'white', marginBottom: '20px', textAlign: 'center' }}>{file.filename}</h3>
            <img
              src={`/api/thumbnails/${file.id}`}
              alt="Audio Placeholder"
              style={{ width: '300px', height: '300px', objectFit: 'cover', borderRadius: '10px', marginBottom: '20px' }}
            />
            <audio
              ref={videoRef}
              src={videoUrl}
              controls
              onClick={(e) => e.stopPropagation()}
              style={{ width: '100%', maxWidth: '500px' }}
            />
          </div>
        ) : (
          <video
            ref={videoRef}
            src={videoUrl}
            controls
            loop
            onClick={(e) => e.stopPropagation()}
          />
        )}
      </div>

      {showControls && index === currentIndex && (
        <div
          className={`slide-info ${showExif ? 'expanded' : ''} ${!controlsVisible ? 'hidden' : ''}`}
          ref={slideInfoRef}
          onClick={handleInfoBarClick}
        >
          {showExif ? (
            <ExifTable data={exifData} />
          ) : (
            // Only show controls when EXIF is hidden
            <div className="viewer-controls">
              {file.type === 'image' && <button title="Show EXIF (i)" aria-label="Show EXIF" onClick={handleShowExif}>ℹ️</button>}
              <button title={file.liked ? "Unlike (l)" : "Like (l)"} aria-label={file.liked ? "Unlike" : "Like"} onClick={handleLikeClick} className="heart-button">
                <HeartIcon liked={file.liked} size={20} />
              </button>
              <button title="Delete (d)" aria-label="Delete" onClick={handleDeleteClick}>🗑️</button>
              {/* ✅ Add Close button here */}
              <button title="Close Viewer (Esc)" aria-label="Close Viewer" onClick={handleCloseClick}>&times;</button>
            </div>
          )}
          {/* Show controls again when EXIF is expanded */}
          {showExif && (
            <div className="viewer-controls">
              {file.type === 'image' && <button title="Hide EXIF (i)" aria-label="Hide EXIF" onClick={handleShowExif}>ℹ️</button>}
              <button title={file.liked ? "Unlike (l)" : "Like (l)"} aria-label={file.liked ? "Unlike" : "Like"} onClick={handleLikeClick} className="heart-button">
                <HeartIcon liked={file.liked} size={20} />
              </button>
              <button title="Delete (d)" aria-label="Delete" onClick={handleDeleteClick}>🗑️</button>
              {/* ✅ Add Close button here too */}
              <button title="Close Viewer (Esc)" aria-label="Close Viewer" onClick={handleCloseClick}>&times;</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MediaSlide;