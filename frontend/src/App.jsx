import { useState, useEffect, useCallback } from 'react';
import Gallery from './components/Gallery';
import Viewer from './components/Viewer';
import './App.css';

function App() {
  const [files, setFiles] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [showFullSize, setShowFullSize] = useState(false);
  const [sortOrder, setSortOrder] = useState('default'); // 'default' or 'random'

  const fetchFiles = useCallback(async () => {
    try {
      const url = `/api/files${sortOrder === 'random' ? '?sort=random' : ''}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      setFiles(data);
    } catch (error) {
      console.error("Failed to fetch files:", error);
      setFiles([]);
    }
  }, [sortOrder]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleShuffle = () => {
    setSortOrder(prev => (prev === 'random' ? 'default' : 'random'));
  };

  const handleLike = async (filename) => {
    try {
      await fetch(`/api/like/${filename}`, { method: 'POST' });
      fetchFiles();
    } catch (error) {
      console.error("Failed to like file:", error);
    }
  };

  const handleDelete = async (filename) => {
    if (window.confirm(`Are you sure you want to delete ${filename}?`)) {
      try {
        await fetch(`/api/delete/${filename}`, { method: 'DELETE' });
        fetchFiles();
      } catch (error) {
        console.error("Failed to delete file:", error);
      }
    }
  };
  
  const openViewer = (index) => setCurrentIndex(index);
  const closeViewer = () => setCurrentIndex(null);

  return (
    <div className="app-container">
      <h1>Media Gallery</h1>
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
      
      <Gallery files={files} onImageClick={openViewer} />

      {currentIndex !== null && (
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
    </div>
  );
}

export default App;