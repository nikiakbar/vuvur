import React from 'react';

function ScanningDisplay({ progress, total }) {
  const percent = total > 0 ? Math.round((progress / total) * 100) : 0;
  return (
    <div className="scanning-container">
      <h2>Scanning Library...</h2>
      <p>Please wait, this may take a few minutes for a large collection.</p>
      <progress value={progress} max={total}></progress>
      <p>{percent}% Complete</p>
      <p>({progress} / {total} files scanned)</p>
    </div>
  );
}

export default ScanningDisplay;