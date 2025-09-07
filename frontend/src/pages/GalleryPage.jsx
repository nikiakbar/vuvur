import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';
import useDebounce from '../useDebounce';
import ScanningDisplay from '../components/ScanningDisplay';

function GalleryPage({ batchSize, showFullSize, setShowFullSize, zoomLevel }) {
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

  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  const fetchFiles = useCallback(async (isNewSearch = false) => {
    setIsLoading(true);
    try {
      const currentPage = isNewSearch ? 1 : page;
      const params = new URLSearchParams({
        sort: sortBy,
        q: debouncedFilenameQuery,
        exif_q: debouncedExifQuery,
        page: currentPage,
        limit: batchSize
      });
      const url = `/api/files?${params.toString()}`;
      const response = await fetch(url);
      const data = await response.json();
      
      if (data.items && Array.isArray(data.items)) {
        setFiles(prevFiles => (isNewSearch ? data.items : [...prevFiles, ...data.items]));
        setTotalPages(data.total_pages);
        setScanStatus({ status: 'complete' });
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
    } finally {
      setIsLoading(false);
    }
  }, [sortBy, debouncedFilenameQuery, debouncedExifQuery, page, batchSize]);

  // Effect for polling the scan status
  useEffect(() => {
    let intervalId;
    if (scanStatus?.status === 'scanning') {
      intervalId = setInterval(async () => {
        const res = await fetch('/api/scan-status');
        const data = await res.json();
        setScanStatus(data);
        if (data.status === 'complete') {
          fetchFiles(true); // Fetch files once scan is complete
          clearInterval(intervalId);
        }
      }, 2000);
    }
    return () => clearInterval(intervalId);
  }, [scanStatus?.status, fetchFiles]);

  // Effect for handling filter/sort changes (This also runs on mount, fetching initial data)
  useEffect(() => {
    setPage(1); // Reset to page 1 on any filter change
    fetchFiles(true); // Fetch as a new search
  }, [sortBy, debouncedFilenameQuery, debouncedExifQuery, fetchFiles]);

  // Effect for loading next page
  useEffect(() => {
    if (page > 1) {
      fetchFiles(false); // Fetch the next page (not a new search)
    }
  }, [page, fetchFiles]);
  
  // THE REDUNDANT "initial load" useEffect has been REMOVED.
  
  const handleLike = async (filePath) => {
    await fetch(`/api/like/${filePath}`, { method: 'POST' });
    setFiles(files.filter(f => f.path !== filePath));
    if (currentIndex !== null && files[currentIndex]?.path === filePath) setCurrentIndex(null);
  };
  const handleDelete = async (filePath) => {
    if (window.confirm(`Are you sure you want to delete ${filePath}?`)) {
      await fetch(`/api/delete/${filePath}`, { method: 'DELETE' });
      setFiles(files.filter(f => f.path !== filePath));
      if (currentIndex !== null && files[currentIndex]?.path === filePath) setCurrentIndex(null);
    }
  };
  
  const openViewer = (index) => setCurrentIndex(index);
  const closeViewer = () => setCurrentIndex(null);

  const visibleFiles = files.slice(0, visibleCount);

  if (!scanStatus) {
    return <div>Loading...</div>; // Initial state before first fetch attempt
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
      {isLoading && page > 1 && <div className="loading-spinner"></div>}

      {currentIndex !== null && files.length > 0 && (
        <Viewer
          files={files}
          currentIndex={currentIndex}
          onClose={closeViewer}
          onLike={handleLike}
          onDelete={handleDelete}
          showFullSize={showFullSize} 
          setCurrentIndex={setCurrentIndex}
          zoomLevel={zoomLevel}
        />
      )}
    </>
  );
}

export default GalleryPage;