import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';
import useDebounce from '../useDebounce';
import ScanningDisplay from '../components/ScanningDisplay';

function GalleryPage({ showFullSize, setShowFullSize }) {
  const batchSize = 20;
  const zoomLevel = 2.5;

  // State for gallery data
  const [files, setFiles] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(null);
  
  // State for controls and pagination
  const [sortBy, setSortBy] = useState('random');
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 500);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // State for scan progress
  const [scanStatus, setScanStatus] = useState({
    scan_complete: false,
    progress: 0,
    total: 0,
  });

  // Effect to poll for scan status
  useEffect(() => {
    const checkScanStatus = async () => {
      try {
        const response = await fetch('/api/scan/status');
        const data = await response.json();
        setScanStatus(data);
        if (data.scan_complete) {
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Failed to check scan status:", error);
        setScanStatus(prev => ({ ...prev, scan_complete: true })); // Stop on error
      }
    };

    const intervalId = setInterval(checkScanStatus, 2000);
    checkScanStatus(); // Initial check

    return () => clearInterval(intervalId);
  }, []);

  // Effect to fetch data when page, sort, or query changes
  useEffect(() => {
    // Only fetch data if the initial scan is complete
    if (!scanStatus.scan_complete) return;

    setIsLoading(true);
    const params = new URLSearchParams({
      sort: sortBy,
      q: debouncedQuery,
      page: page,
      limit: batchSize
    });

    fetch(`/api/gallery?${params.toString()}`)
      .then(res => res.json())
      .then(data => {
        if (data && data.items && Array.isArray(data.items)) {
          setFiles(prev => (page === 1 ? data.items : [...prev, ...data.items]));
          setHasMore(page < data.total_pages);
        }
        setIsLoading(false);
      })
      .catch(() => {
        setIsLoading(false);
      });
  }, [scanStatus.scan_complete, page, sortBy, debouncedQuery, batchSize]);

  // Effect to reset the gallery when the user changes sort/search
  useEffect(() => {
    setPage(1);
    setFiles([]); // Clear existing files to trigger a new fetch
  }, [sortBy, debouncedQuery]);

  // Infinite scroll observer
  const observer = useRef();
  const lastImageElementRef = useCallback(node => {
    if (isLoading) return;
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        setPage(prevPage => prevPage + 1);
      }
    });
    if (node) observer.current.observe(node);
  }, [isLoading, hasMore]);


  // --- Action Handlers ---
  const handleLike = async (fileId) => {
    try {
      await fetch(`/api/toggle_like/${fileId}`, { method: 'POST' });
      setFiles(files.filter(f => f.id !== fileId));
      // Close viewer if the liked image was the last one
      if (files.length === 1) setCurrentIndex(null);
    } catch (error) {
      console.error("Failed to like file:", error);
    }
  };

  // NOTE: A backend endpoint for deleting files is not yet implemented.
  const handleDelete = (fileId) => {
    if (window.confirm(`Are you sure you want to delete this file? Note: This only removes it from the view for now.`)) {
        setFiles(files.filter(f => f.id !== fileId));
        if (files.length === 1) setCurrentIndex(null);
    }
  };

  const openViewer = (index) => setCurrentIndex(index);
  const closeViewer = () => setCurrentIndex(null);

  // --- Render Logic ---
  if (!scanStatus.scan_complete) {
    return <ScanningDisplay progress={scanStatus.progress} total={scanStatus.total} />;
  }

  return (
    <>
      <div className="controls-bar settings">
        <input
          type="text"
          placeholder="Search filename or EXIF..."
          className="filter-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
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
            <label htmlFor="full-size-toggle">Show Full-Size in Viewer</label>
        </div>
      </div>

      <Gallery
        files={files}
        onImageClick={openViewer}
        lastImageRef={lastImageElementRef}
      />
      {isLoading && page > 1 && <div className="loading-spinner"></div>}

      {currentIndex !== null && files.length > 0 && (
        <Viewer
          files={files}
          currentIndex={currentIndex}
          onClose={closeViewer}
          onLike={() => handleLike(files[currentIndex]?.id)}
          onDelete={() => handleDelete(files[currentIndex]?.id)}
          showFullSize={showFullSize}
          setCurrentIndex={setCurrentIndex}
          zoomLevel={zoomLevel}
        />
      )}
    </>
  );
}

export default GalleryPage;