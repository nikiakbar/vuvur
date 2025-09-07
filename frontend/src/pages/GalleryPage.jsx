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
  const [files, setFiles] = useState([]); // This now holds ONLY the visible files
  const [scanStatus, setScanStatus] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(null);
  
  const [sortBy, setSortBy] = useState('random');
  const [filenameQuery, setFilenameQuery] = useState('');
  const [exifQuery, setExifQuery] = useState('');

  // --- New Pagination State ---
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  const debouncedFilenameQuery = useDebounce(filenameQuery, 500);
  const debouncedExifQuery = useDebounce(exifQuery, 500);
  
  const observer = useRef();
  
  // Infinite scroll trigger: when the last element is visible, increment the page
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

  // Main file fetching function, now paginated
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
        // If it's a new search, replace files. If it's a new page, append them.
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
          fetchFiles(true); // Trigger a new search
          clearInterval(intervalId);
        }
      }, 2000);
    }
    return () => clearInterval(intervalId);
  }, [scanStatus?.status, fetchFiles]);

  // Effect for handling filter/sort changes (triggers a new search)
  useEffect(() => {
    setPage(1); // Reset to page 1
    fetchFiles(true); // Pass true to signal a new search
  }, [sortBy, debouncedFilenameQuery, debouncedExifQuery]);

  // Effect for loading next page
  useEffect(() => {
    if (page > 1) {
      fetchFiles(false); // Fetch next page (not a new search)
    }
  }, [page, fetchFiles]);
  
  // --- Action Handlers (Like/Delete) ---
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

  // --- Render Logic ---
  if (!scanStatus) return <div>Loading...</div>;
  if (scanStatus.status === 'scanning') {
    return <ScanningDisplay progress={scanStatus.progress} total={scanStatus.total} />;
  }

  return (
    <>
      <div className="controls-bar settings">
        <input type="text" placeholder="Filter by filename..." className="filter-input" value={filenameQuery} onChange={(e) => setFilenameQuery(e.target.value)} />
        <input type="text" placeholder="Search prompts/EXIF..." className="filter-input" value={exifQuery} onChange={(e) => setExifQuery(e.target.value)} />
        <select className="sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="random">Random</option>
          <option value="date_desc">Date (Newest First)</option>
          <option value="date_asc">Date (Oldest First)</option>
          <option value="file_asc">Filename (A-Z)</option>
          <option value="file_desc">Filename (Z-A)</option>
        </select>
        <div className="setting-item">
            <input type="checkbox" id="full-size-toggle" checked={showFullSize} onChange={(e) => setShowFullSize(e.target.checked)} />
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
        />
      )}
    </>
  );
}

export default GalleryPage;