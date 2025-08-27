import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';

const BATCH_SIZE = 50; // How many images to load at a time

function GalleryPage() {
  const [files, setFiles] = useState([]);
  const [visibleCount, setVisibleCount] = useState(BATCH_SIZE);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [showFullSize, setShowFullSize] = useState(false);
  const [sortOrder, setSortOrder] = useState('default');
  
  const observer = useRef();
  
  // This callback ref is attached to the last element in the list.
  // When it becomes visible, we load more images.
  const lastImageElementRef = useCallback(node => {
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && files.length > visibleCount) {
        setVisibleCount(prev => prev + BATCH_SIZE);
      }
    });
    if (node) observer.current.observe(node);
  }, [files.length, visibleCount]);

  const fetchFiles = useCallback(async () => {
    try {
      const url = `/api/files${sortOrder === 'random' ? '?sort=random' : ''}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      setFiles(data);
    } catch (error) {
      console.error("Failed to fetch files:", error);
      setFiles([]);
    }
  }, [sortOrder]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleShuffle = () => {
    setVisibleCount(BATCH_SIZE); // Reset visible count on shuffle
    setSortOrder(prev => (prev === 'random' ? 'default' : 'random'));
  };

  const handleLike = async (filePath) => {
    try {
      await fetch(`/api/like/${filePath}`, { method: 'POST' });
      fetchFiles();
      if (currentIndex !== null && files[currentIndex]?.path === filePath) {
        setCurrentIndex(null);
      }
    } catch (error) {
      console.error("Failed to like file:", error);
    }
  };

  const handleDelete = async (filePath) => {
    if (window.confirm(`Are you sure you want to delete ${filePath}?`)) {
      try {
        await fetch(`/api/delete/${filePath}`, { method: 'DELETE' });
        fetchFiles();
        if (currentIndex !== null && files[currentIndex]?.path === filePath) {
          setCurrentIndex(null);
        }
      } catch (error) {
        console.error("Failed to delete file:", error);
      }
    }
  };
  
  const openViewer = (index) => setCurrentIndex(index);
  const closeViewer = () => setCurrentIndex(null);

  // We only pass the visible slice of files to the Gallery
  const visibleFiles = files.slice(0, visibleCount);

  return (
    <>
      <div className="settings">
        <div className="setting-item">
            <input
              type="checkbox"
              id="full-size-toggle"
              checked={showFullSize}
              onChange={(e) => setShowFullSize(e.target.checked)}
            />
            <label htmlFor="full-size-toggle">Show Full-Size</label>
        </div>
        <button onClick={handleShuffle} className="shuffle-button">
            {sortOrder === 'random' ? 'Sorted Order' : 'Shuffle'}
        </button>
      </div>
      
      <Gallery 
        files={visibleFiles} 
        onImageClick={openViewer} 
        lastImageRef={lastImageElementRef}
      />

      {currentIndex !== null && files.length > 0 && (
        <Viewer
          files={files} // The viewer still needs the full list to navigate
          currentIndex={currentIndex}
          onClose={closeViewer}
          onLike={handleLike}
          onDelete={handleDelete}
          showFullSize={showFullSize}
          setCurrentIndex={setCurrentIndex}
        />
      )}
    </>
  );
}

export default GalleryPage;