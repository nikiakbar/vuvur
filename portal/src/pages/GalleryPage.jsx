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
  const [initialIndex, setInitialIndex] = useState(null); // Changed from currentIndex
  
  // State for controls and pagination
  const [sortBy, setSortBy] = useState('random');
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 500);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [groups, setGroups] = useState([]); // State for quick-access groups
  const [selectedGroup, setSelectedGroup] = useState(''); // State for active group

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
  
  // Effect to fetch quick-access groups
  useEffect(() => {
    if (!scanStatus.scan_complete) return;

    const fetchGroups = async () => {
      try {
        const response = await fetch('/api/gallery/groups');
        const data = await response.json();
        setGroups(data);
      } catch (error) {
        console.error("Failed to fetch groups:", error);
      }
    };
    fetchGroups();
  }, [scanStatus.scan_complete]);

  // Effect to fetch data when page, sort, or query changes
  useEffect(() => {
    if (!scanStatus.scan_complete) return;

    setIsLoading(true);
    const params = new URLSearchParams({
      sort: sortBy,
      q: debouncedQuery,
      page: page,
      limit: batchSize,
      group: selectedGroup // Add group filter to API call
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
  }, [scanStatus.scan_complete, page, sortBy, debouncedQuery, batchSize, selectedGroup]); // Add selectedGroup dependency

  // Effect to reset the gallery when the user changes sort/search/group
  useEffect(() => {
    setPage(1);
    setFiles([]);
  }, [sortBy, debouncedQuery, selectedGroup]); // Add selectedGroup dependency

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
      if (files.length === 1) setInitialIndex(null);
    } catch (error) {
      console.error("Failed to like file:", error);
    }
  };

const handleDelete = async (fileId) => {
    // The confirmation "if" statement has been removed.
    try {
      // Call the backend endpoint immediately
      const response = await fetch(`/api/delete/${fileId}`, { method: 'POST' });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete file.');
      }

      // If the API call is successful, then update the UI
      setFiles(files.filter(f => f.id !== fileId));
      // Close the viewer if the last image was deleted
      if (files.length === 1) setInitialIndex(null);

    } catch (error) {
      console.error("Failed to delete file:", error);
      alert(`Error: ${error.message}`); // Show an error message to the user
    }
  };

  const openViewer = (index) => setInitialIndex(index);
  const closeViewer = () => setInitialIndex(null);

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

      {groups.length > 0 && (
        <div className="quick-access-bar">
          <button 
            className={`quick-access-button ${selectedGroup === '' ? 'active' : ''}`}
            onClick={() => setSelectedGroup('')}
          >
            All
          </button>
          {groups.map(group => (
            <button 
              key={group.group_tag}
              className={`quick-access-button ${selectedGroup === group.group_tag ? 'active' : ''}`}
              onClick={() => setSelectedGroup(group.group_tag)}
            >
              {group.group_tag} ({group.count})
            </button>
          ))}
        </div>
      )}

      <Gallery
        files={files}
        onImageClick={openViewer}
        lastImageRef={lastImageElementRef}
      />
      {isLoading && page > 1 && <div className="loading-spinner"></div>}

      {initialIndex !== null && files.length > 0 && (
        <Viewer
          files={files}
          initialIndex={initialIndex}
          onClose={closeViewer}
          onLike={handleLike}
          onDelete={handleDelete}
          showFullSize={showFullSize}
          zoomLevel={zoomLevel}
        />
      )}
    </>
  );
}

export default GalleryPage;