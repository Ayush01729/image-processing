import React, { useState } from 'react';
import './App.css'

function App() {
  const [files, setFiles] = useState([]);
  const [uploads, setUploads] = useState([]);

  const handleFileChange = (e, index) => {
    const updatedFiles = [...files];
    updatedFiles[index] = e.target.files[0];
    setFiles(updatedFiles);
  };

  const handleUpload = async (index) => {
    const formData = new FormData();
    formData.append('file', files[index]);

    try {
      const response = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      const newUploads = [...uploads];
      newUploads[index] = { requestId: data.request_id, status: 'Pending', downloadUrl: '' };
      setUploads(newUploads);
    } catch (error) {
      console.error('Error uploading file:', error);
    }
  };

  const checkStatus = async (index) => {
    const { requestId } = uploads[index];
    try {
      const response = await fetch(`http://localhost:5000/check_task/${requestId}`);
      const data = await response.json();
      const newUploads = [...uploads];
      newUploads[index].status = data.status;
      newUploads[index].downloadUrl = data.status === 'SUCCESS' ? `http://localhost:5000/download/${requestId}` : '';
      setUploads(newUploads);
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const addUploadSection = () => {
    setFiles([...files, null]);
    setUploads([...uploads, { requestId: '', status: 'Pending', downloadUrl: '' }]);
  };

  return (
    <div className="App">
      <h1>Image Processing System</h1>
      {uploads.map((upload, index) => (
        <div key={index}>
          <input type="file" onChange={(e) => handleFileChange(e, index)} />
          <button onClick={() => handleUpload(index)}>Upload CSV</button>
          <br />
          {upload.requestId && (
            <div>
              <p>Request ID: {upload.requestId}</p>
              <button onClick={() => checkStatus(index)}>Check Status</button>
              {upload.status && <p>Status: {upload.status}</p>}
              {upload.status === 'SUCCESS' && (
                <div>
                  <a href={upload.downloadUrl} download>
                    <button>Download File</button>
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
      <button onClick={addUploadSection}>Add Another Upload</button>
    </div>
  );
}

export default App;

