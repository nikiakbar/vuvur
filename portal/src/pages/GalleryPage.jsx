// portal/src/pages/GalleryPage.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import Gallery from '../components/Gallery';
import Viewer from '../components/Viewer';
import useDebounce from '../useDebounce';
import ScanningDisplay from '../components/ScanningDisplay';

function GalleryPage() {
  const batchSize = 20; // Consider making this configurable via env var if needed
  const zoomLevel = 2.5; // Consider making this configurable via env var if needed

  // State for gallery data
  const [files, setFiles] = useState([]);
  const [initialIndex, setInitialIndex] = useState(null);

  // State for controls and pagination
  const [sortBy, setSortBy] = useState('random');
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 500);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [groups, setGroups] = useState([]); // Top-level groups
  const [selectedGroup, setSelectedGroup] = useState(''); // Active top-level group
  const [subgroups, setSubgroups] = useState([]); // Second-level subgroups
  const [selectedSubgroup, setSelectedSubgroup] = useState(''); // Active subgroup
  const [isLoadingSubgroups, setIsLoadingSubgroups] = useState(false);


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
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setScanStatus(data);
        if (data.scan_complete) {
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Failed to check scan status:", error);
        // Assume scan complete on error to avoid blocking UI indefinitely
        setScanStatus(prev => ({ ...prev, scan_complete: true }));
        clearInterval(intervalId); // Stop polling on error
      }
    };

    const intervalId = setInterval(checkScanStatus, 2000);
    checkScanStatus(); // Initial check

    return () => clearInterval(intervalId);
  }, []);

  // Effect to fetch top-level groups
  useEffect(() => {
    if (!scanStatus.scan_complete) return;

    const fetchGroups = async () => {
      try {
        const response = await fetch('/api/gallery/groups');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setGroups(data);
      } catch (error) {
        console.error("Failed to fetch groups:", error);
      }
    };
    fetchGroups();
  }, [scanStatus.scan_complete]);

   // Effect to fetch subgroups when a top-level group is selected
  useEffect(() => {
    if (!selectedGroup) {
      setSubgroups([]); // Clear subgroups if no group is selected
      setSelectedSubgroup(''); // Clear subgroup selection
      return;
    }

    const fetchSubgroups = async () => {
       setIsLoadingSubgroups(true);
      try {
        const params = new URLSearchParams({ group: selectedGroup });
        const response = await fetch(`/api/gallery/subgroups?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setSubgroups(data);
      } catch (error) {
        console.error(`Failed to fetch subgroups for ${selectedGroup}:`, error);
        setSubgroups([]); // Clear on error
      } finally {
          setIsLoadingSubgroups(false);
      }
    };
    fetchSubgroups();
  }, [selectedGroup]); // Re-run when selectedGroup changes


  // Effect to fetch gallery data (now depends on subgroup too)
  useEffect(() => {
    if (!scanStatus.scan_complete) return;

    setIsLoading(true);
    const params = new URLSearchParams({
      sort: sortBy,
      q: debouncedQuery,
      page: page,
      limit: batchSize,
      group: selectedGroup,
      subgroup: selectedSubgroup // Pass selected subgroup
    });

    fetch(`/api/gallery?${params.toString()}`)
      .then(res => {
         if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
         return res.json();
      })
      .then(data => {
        if (data && data.items && Array.isArray(data.items)) {
          setFiles(prev => (page === 1 ? data.items : [...prev, ...data.items]));
          setHasMore(page < data.total_pages);
        } else {
             // Handle case where API might return unexpected structure
             console.warn("Received unexpected data structure from /api/gallery:", data);
             setFiles(prev => (page === 1 ? [] : prev)); // Clear on page 1 if data bad
             setHasMore(false);
        }
        setIsLoading(false);
      })
      .catch((error) => {
         console.error("Failed to fetch gallery:", error);
        setIsLoading(false);
         // Optionally show an error message to the user here
      });
      // Add selectedSubgroup dependency
  }, [scanStatus.scan_complete, page, sortBy, debouncedQuery, batchSize, selectedGroup, selectedSubgroup]);

  // Effect to reset gallery/pagination when filters change
  useEffect(() => {
    setPage(1);
    setFiles([]);
    // Only reset subgroup if the main group changes
    if (selectedSubgroup && !selectedGroup) {
         setSelectedSubgroup('');
    }
     // Add selectedSubgroup dependency
  }, [sortBy, debouncedQuery, selectedGroup, selectedSubgroup]);

  // Infinite scroll observer (no changes needed here)
  const observer = useRef();
  const lastImageElementRef = useCallback(node => {
     // ... (observer logic remains the same) ...
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
     // ... (like logic remains the same) ...
     try {
      await fetch(`/api/toggle_like/${fileId}`, { method: 'POST' });
      setFiles(files.filter(f => f.id !== fileId));
      if (files.length === 1) setInitialIndex(null); // Close viewer if last image removed
      // Adjust index if needed after deletion (more complex, skip for now)
    } catch (error) {
      console.error("Failed to like file:", error);
    }
  };

  const handleDelete = async (fileId) => {
     // ... (delete logic remains the same) ...
      try {
      const response = await fetch(`/api/delete/${fileId}`, { method: 'POST' });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete file.');
      }
      setFiles(files.filter(f => f.id !== fileId));
      if (files.length === 1) setInitialIndex(null); // Close viewer if last image removed
       // Adjust index if needed after deletion (more complex, skip for now)
    } catch (error) {
      console.error("Failed to delete file:", error);
      alert(`Error: ${error.message}`);
    }
  };

  const openViewer = (index) => setInitialIndex(index);
  const closeViewer = () => setInitialIndex(null);

  // --- Filter Selection Handlers ---
   const handleGroupSelect = (groupTag) => {
       setSelectedGroup(groupTag);
       setSelectedSubgroup(''); // Reset subgroup when main group changes
   };

   const handleSubgroupSelect = (subgroupTag) => {
        setSelectedSubgroup(subgroupTag);
   };


  // --- Render Logic ---
  if (!scanStatus.scan_complete) {
    return <ScanningDisplay progress={scanStatus.progress} total={scanStatus.total} />;
  }

  return (
    <>
      {/* Search and Sort Bar (remains the same) */}
      <div className="controls-bar settings">
         {/* ... (input and select elements remain the same) ... */}
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
      </div>

      {/* Top-Level Group Buttons */}
      {groups.length > 0 && (
        <div className="quick-access-bar group-bar">
          <button
            className={`quick-access-button ${selectedGroup === '' ? 'active' : ''}`}
            onClick={() => handleGroupSelect('')}
          >
            All
          </button>
          {groups.map(group => (
            <button
              key={group.group_tag}
              className={`quick-access-button ${selectedGroup === group.group_tag ? 'active' : ''}`}
              onClick={() => handleGroupSelect(group.group_tag)}
            >
              {group.group_tag} ({group.count})
            </button>
          ))}
        </div>
      )}

       {/* Subgroup Buttons (only show if a group is selected and subgroups exist or are loading) */}
       {(selectedGroup && (subgroups.length > 0 || isLoadingSubgroups)) && (
           <div className="quick-access-bar subgroup-bar">
               {isLoadingSubgroups ? (
                   <span className="loading-subgroups">Loading subfolders...</span>
               ) : (
                   <>
                       <button
                           className={`quick-access-button ${selectedSubgroup === '' ? 'active' : ''}`}
                           onClick={() => handleSubgroupSelect('')}
                       >
                           All '{selectedGroup}'
                       </button>
                       {subgroups.map(subgroupName => (
                           <button
                               key={subgroupName}
                               className={`quick-access-button ${selectedSubgroup === subgroupName ? 'active' : ''}`}
                               onClick={() => handleSubgroupSelect(subgroupName)}
                           >
                               {subgroupName}
                           </button>
                       ))}
                   </>
               )}
           </div>
       )}


      {/* Gallery Grid */}
      <Gallery
        files={files}
        onImageClick={openViewer}
        lastImageRef={lastImageElementRef}
      />
      {/* Loading spinner for pagination */}
      {isLoading && page > 1 && <div className="loading-spinner"></div>}

      {/* Viewer Modal */}
      {initialIndex !== null && files.length > 0 && (
        <Viewer
          files={files}
          initialIndex={initialIndex}
          onClose={closeViewer}
          onLike={handleLike}
          onDelete={handleDelete}
          zoomLevel={zoomLevel}
        />
      )}
    </>
  );
}

export default GalleryPage;