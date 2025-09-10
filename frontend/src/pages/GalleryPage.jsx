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
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 500);
  
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  
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

  useEffect(() => {
    setPage(1);
  }, [sortBy, debouncedQuery]);
  
  useEffect(() => {
    const fetchData = async () => {
      const isNewSearch = page === 1;
      setIsLoading(true);
      try {
        const params = new URLSearchParams({
          sort: sortBy,
          q: debouncedQuery,
          page: page,
          limit: batchSize
        });
        const url = `/api/media?${params.toString()}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.items && Array.isArray(data.items)) {
          setFiles(prev => isNewSearch ? data.items : [...prev, ...data.items]);
          setTotalPages(data.total_pages);
          setScanStatus({ status: 'complete' });
        } else if (data.status === 'scanning') {
          setScanStatus(data);
          setFiles([]);
        } else {
          setFiles([]);
        }
      } catch (error) {
        setFiles([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    const checkStatusAndFetch = async () => {
        const res = await fetch('/api/scan-status');
        const data = await res.json();
        setScanStatus(data);
        if (data.status === 'complete') {
            fetchData();
        }
    };

    if (!scanStatus || scanStatus.status !== 'scanning') {
        checkStatusAndFetch();
    }
  }, [page, sortBy, debouncedQuery, batchSize, scanStatus]);

  useEffect(() => {
    let intervalId;
    if (scanStatus?.status === 'scanning') {
      intervalId = setInterval(async () => {
        const res = await fetch('/api/scan-status');
        const data = await res.json();
        setScanStatus(data);
        if (data.status === 'complete') {
          clearInterval(intervalId);
          setPage(1);
        }
      }, 2000);
    }
    return () => clearInterval(intervalId);
  }, [scanStatus?.status]);
  
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

  if (!scanStatus) { return <div>Loading...</div>; }
  if (scanStatus.status === 'scanning') {
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