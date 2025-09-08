import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';
import useDebounce from '../useDebounce';
import ScanningDisplay from '../components/ScanningDisplay';
import { useSettings } from '../contexts/SettingsContext';

function GalleryPage() {
  const { settings } = useSettings();
  const batchSize = settings?.batch_size || 20;
  const zoomLevel = settings?.zoom_level || 2.5;

  const [files, setFiles] = useState([]);
  const [scanStatus, setScanStatus] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [showFullSize, setShowFullSize] = useState(false);
  
  const [sortBy, setSortBy] = useState('random');
  const [filenameQuery, setFilenameQuery] = useState('');
  const [exifQuery, setExifQuery] = useState('');

  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  const debouncedFilenameQuery = useDebounce(filenameQuery, 500);
  const debouncedExifQuery = useDebounce(exifQuery, 500);
  
  const observer = useRef();

  const lastImageElementRef = useCallback(node => {
    if (isLoading) return;
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && page < totalPages) {
        setPage(prevPage => prevPage + 1);
      }
    });
    if (node) observer.current.observe(node);
  }, [isLoading, page, totalPages]);

  // This effect now ONLY handles resetting the page when filters change
  useEffect(() => {
    setPage(1);
  }, [sortBy, debouncedFilenameQuery, debouncedExifQuery]);

  // This single effect handles ALL data fetching
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      const isNewSearch = page === 1; // Any fetch on page 1 is a new search
      try {
        const params = new URLSearchParams({
          sort: sortBy,
          q: debouncedFilenameQuery,
          exif_q: debouncedExifQuery,
          page: page,
          limit: batchSize
        });
        const url = `/api/files?${params.toString()}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.items && Array.isArray(data.items)) {
          setFiles(prev => isNewSearch ? data.items : [...prev, ...data.items]);
          setTotalPages(data.total_pages);
          setScanStatus({ status: 'complete' });
        } else if (data.status === 'scanning') {
          setScanStatus(data);
          setFiles([]); // Clear files while scanning
        } else {
          console.error("API error or bad data:", data);
          setFiles([]);
        }
      } catch (error) {
        console.error("Failed to fetch files:", error);
        setFiles([]);
      } finally {
        setIsLoading(false);
      }
    };

    const fetchScanStatus = async () => {
      const res = await fetch('/api/scan-status');
      const data = await res.json();
      setScanStatus(data);
      if (data.status === 'complete') {
        fetchData(); // Scan is done, fetch data
      }
    };
    
    // Polling logic
    if (scanStatus?.status === 'scanning') {
      const intervalId = setInterval(fetchScanStatus, 2000);
      return () => clearInterval(intervalId);
    } else {
      // If not scanning, just fetch the data
      fetchData();
    }
  // We only want this main fetch logic to re-run when these key values change
  }, [page, sortBy, debouncedFilenameQuery, debouncedExifQuery, batchSize]);


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