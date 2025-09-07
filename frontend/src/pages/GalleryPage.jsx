import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';
import { useDebounce } from '../useDebounce';

function ScanningDisplay({ progress, total }) {
  const percent = total > 0 ? Math.round((progress / total) * 100) : 0;
  return (
    <div className="scanning-container">
      <h2>Scanning Library...</h2>
      <p>Please wait, this may take several minutes for a large collection...</p>
      <progress value={progress} max={total}></progress>
      <p>{percent}% Complete</p>
      <p>({progress} / {total} files scanned)</p>
    </div>
  );
}

function GalleryPage({ batchSize, showFullSize, setShowFullSize }) {
  const [files, setFiles] = useState([]);
  const [scanStatus, setScanStatus] = useState(null);
  const [visibleCount, setVisibleCount] = useState(batchSize);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [sortBy, setSortBy] = useState('random');
  const [filenameQuery, setFilenameQuery] = useState('');
  const [exifQuery, setExifQuery] = useState('');

  const debouncedFilenameQuery = useDebounce(filenameQuery, 500);
  const debouncedExifQuery = useDebounce(exifQuery, 500);
  
  const observer = useRef();

  useEffect(() => { setVisibleCount(batchSize) }, [batchSize]);
  
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
      const params = new URLSearchParams({
        sort: sortBy,
        q: debouncedFilenameQuery,
        exif_q: debouncedExifQuery
      });
      const url = `/api/files?${params.toString()}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
      const data = await response.json();
      
      if (Array.isArray(data)) {
        setFiles(data);
        setScanStatus({ status: 'complete' });
        setVisibleCount(batchSize); 
      } else if (data.status === 'scanning') {
        setScanStatus(data);
        setFiles([]);
      } else {
        console.error("API did not return an array:", data);
        setFiles([]);
      }
    } catch (error) {
      console.error("Failed to fetch files:", error);
      setFiles([]);
    }
  }, [sortBy, debouncedFilenameQuery, debouncedExifQuery, batchSize]);

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
  }, [sortBy, debouncedFilenameQuery, debouncedExifQuery, scanStatus?.status, fetchFiles]);
  
  const handleLike = async (filePath) => {
    try {
      await fetch(`/api/like/${filePath}`, { method: 'POST' });
      setFiles(files.filter(f => f.path !== filePath)); // Optimistic UI update
      if (currentIndex !== null && files[currentIndex]?.path === filePath) {
        setCurrentIndex(null);
      }
    } catch (error) { console.error("Failed to like file:", error) }
  };

  const handleDelete = async (filePath) => {
    if (window.confirm(`Are you sure you want to delete ${filePath}?`)) {
      try {
        await fetch(`/api/delete/${filePath}`, { method: 'DELETE' });
        setFiles(files.filter(f => f.path !== filePath)); // Optimistic UI update
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
      <div className="controls-bar settings">
        <input 
          type="text"
          placeholder="Filter by filename..."
          className="filter-input"
          value={filenameQuery}
          onChange={(e) => setFilenameQuery(e.target.value)}
        />
        <input 
          type="text"
          placeholder="Search prompts/EXIF..."
          className="filter-input"
          value={exifQuery}
          onChange={(e) => setExifQuery(e.target.value)}
        />
        <select className="sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="random">Random</option>
          <option value="date_desc">Date (Newest First)</option>
          <option value="date_asc">Date (Oldest First)</option>
          <option value="file_asc">Filename (A-Z)</option>
          <option value="file_desc">Filename (Z-A)</option>
        </select>
        <div className="setting-item">
            <input
              type="checkbox"
              id="full-size-toggle"
              checked={showFullSize} 
              onChange={(e) => setShowFullSize(e.target.checked)}
            />
            <label htmlFor="full-size-toggle">Show Full-Size</label>
        </div>
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