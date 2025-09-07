import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';
import { useDebounce } from '../useDebounce';

function ScanningDisplay({ progress, total }) {
  // ... (unchanged) ...
  const percent = total > 0 ? Math.round((progress / total) * 100) : 0;
  return (
    <div className="scanning-container">
      <h2>Scanning Library...</h2>
      <p>Please wait...</p>
      <progress value={progress} max={total}></progress>
      <p>{percent}% Complete</p>
      <p>({progress} / {total} files scanned)</p>
    </div>
  );
}

// Receive zoomLevel prop from App
function GalleryPage({ batchSize, showFullSize, setShowFullSize, zoomLevel }) {
  const [files, setFiles] = useState([]);
  const [scanStatus, setScanStatus] = useState(null);
  const [visibleCount, setVisibleCount] = useState(batchSize);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [sortBy, setSortBy] = useState('random');
  const [filenameQuery, setFilenameQuery] = useState('');
  const [exifQuery, setExifQuery] = useState('');

  // ... (all other hooks and handlers remain the same) ...
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
      if (Array.isArray(data.items)) {
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
  useEffect(() => {
    if (scanStatus?.status !== 'scanning') {
        fetchFiles(true);
    }
  }, [sortBy, debouncedFilenameQuery, debouncedExifQuery]);
  useEffect(() => {
    if (page > 1) {
        fetchFiles(false);
    }
  }, [page]);
  useEffect(() => {
    let intervalId;
    if (scanStatus?.status === 'scanning') {
      intervalId = setInterval(async () => {
        const res = await fetch('/api/scan-status');
        const data = await res.json();
        setScanStatus(data);
        if (data.status === 'complete') {
          fetchFiles(true);
          clearInterval(intervalId);
        }
      }, 2000);
    }
    return () => clearInterval(intervalId);
  }, [scanStatus?.status, fetchFiles]);
  useEffect(() => {
    fetchFiles(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const handleLike = async (filePath) => { /* ... */ };
  const handleDelete = async (filePath) => { /* ... */ };
  const openViewer = (index) => setCurrentIndex(index);
  const closeViewer = () => setCurrentIndex(null);
  const visibleFiles = files.slice(0, visibleCount);
  if (!scanStatus) { return <div>Loading...</div>; }
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
          zoomLevel={zoomLevel} /* Pass the prop down */
        />
      )}
    </>
  );
}

export default GalleryPage;