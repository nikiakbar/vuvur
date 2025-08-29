import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';

const BATCH_SIZE = 50;

function ScanningDisplay({ progress, total }) {
  // ... (This sub-component remains unchanged)
  const percent = total > 0 ? Math.round((progress / total) * 100) : 0;
  return (
    <div className="scanning-container">
      <h2>Scanning Library (First-Time Setup)</h2>
      <p>Please wait, this may take several minutes for a large collection...</p>
      <progress value={progress} max={total}></progress>
      <p>{percent}% Complete</p>
      <p>({progress} / {total} files scanned)</p>
    </div>
  );
}

function GalleryPage({ batchSize }) {
  const [files, setFiles] = useState([]);
  const [scanStatus, setScanStatus] = useState(null);
  const [visibleCount, setVisibleCount] = useState(batchSize);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [showFullSize, setShowFullSize] = useState(false);
  const [sortOrder, setSortOrder] = useState('default');
  
  const observer = useRef();

  const lastImageElementRef = useCallback(node => {
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && files.length > visibleCount) {
        setVisibleCount(prev => prev + batchSize);
      }
    });
    if (node) observer.current.observe(node);
  }, [files.length, visibleCount, batchSize]);

  const fetchFiles = useCallback(async () => {
    try {
      const url = `/api/files${sortOrder === 'random' ? '?sort=random' : ''}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
      const data = await response.json();
      
      // THE FIX: Ensure the data from the API is an array before setting state.
      if (Array.isArray(data)) {
        setFiles(data);
        setScanStatus({ status: 'complete' });
      } else if (data.status === 'scanning') {
        setScanStatus(data);
        setFiles([]); // Ensure files is an empty array during scan
      } else {
        // If we get an object that isn't a scan status, it's an error.
        console.error("API did not return an array:", data);
        setFiles([]); // Fallback to an empty array to prevent crash
      }
    } catch (error) {
      console.error("Failed to fetch files:", error);
      setFiles([]); // Fallback to an empty array on any fetch error
    }
  }, [sortOrder]);

  // Main effect to fetch initial data and poll for scan status
  useEffect(() => {
    fetchFiles();
    
    let intervalId;
    if (scanStatus?.status === 'scanning') {
      intervalId = setInterval(async () => {
        const res = await fetch('/api/scan-status');
        const data = await res.json();
        setScanStatus(data);
        if (data.status === 'complete') {
          fetchFiles();
          clearInterval(intervalId);
        }
      }, 2000);
    }
    
    return () => clearInterval(intervalId);
  }, [sortOrder, scanStatus?.status, fetchFiles]);
  
  // ... (The rest of the component remains unchanged) ...
  useEffect(() => {
    setVisibleCount(batchSize);
  }, [batchSize]);

  const handleShuffle = () => {
    setVisibleCount(batchSize);
    setSortOrder(prev => (prev === 'random' ? 'default' : 'random'));
  };

  const handleLike = async (filePath) => {
    try {
      await fetch(`/api/like/${filePath}`, { method: 'POST' });
      fetchFiles();
      if (currentIndex !== null && files[currentIndex]?.path === filePath) {
        setCurrentIndex(null);
      }
    } catch (error) { console.error("Failed to like file:", error) }
  };

  const handleDelete = async (filePath) => {
    if (window.confirm(`Are you sure you want to delete ${filePath}?`)) {
      try {
        await fetch(`/api/delete/${filePath}`, { method: 'DELETE' });
        fetchFiles();
        if (currentIndex !== null && files[currentIndex]?.path === filePath) {
          setCurrentIndex(null);
        }
      } catch (error) { console.error("Failed to delete file:", error) }
    }
  };
  
  const openViewer = (index) => setCurrentIndex(index);
  const closeViewer = () => setCurrentIndex(null);

  const visibleFiles = files.slice(0, visibleCount);

  if (!scanStatus) {
    return <div>Loading...</div>;
  }
  if (scanStatus.status === 'scanning') {
    return <ScanningDisplay progress={scanStatus.progress} total={scanStatus.total} />;
  }

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
          files={files}
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