import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

interface Note {
  _id: string;
  note: string;
  type?: string;
  filename?: string;
  total_pages?: number;
  created_at: string;
  updated_at: string;
}

interface NotesResponse {
  success: boolean;
  notes: Note[];
  count: number;
  error?: string;
  message?: string;
}

interface ClusterNote {
  _id: string;
  note: string;
  type?: string;
  filename?: string;
  total_pages?: number;
  created_at: string;
  updated_at: string;
}

interface ClusterData {
  [key: string]: ClusterNote[];
}

interface ClustersResponse {
  success: boolean;
  clusters: ClusterData;
  autoK?: boolean;
  maxK?: number;
  message?: string;
  error?: string;
}

interface ClusterSummary {
  total_notes: number;
  num_clusters: number;
  auto_determined_k: boolean;
  clusters: {
    [key: number]: {
      size: number;
      sample_notes: string[];
      notes: ClusterNote[];
    };
  };
}

interface ClusterSummaryResponse {
  success: boolean;
  summary: ClusterSummary;
  autoK?: boolean;
  maxK?: number;
  message?: string;
  error?: string;
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

interface PdfUploadResponse {
  success: boolean;
  pdfId: string;
  filename: string;
  totalPages: number;
  pagesWithText: number;
  fileSizeBytes: number;
  message?: string;
  error?: string;
}

const API_BASE_URL = 'http://localhost:8080';

function normalizeClusters(rawClusters: any): ClusterData {
  if (Array.isArray(rawClusters)) {
    const obj: ClusterData = {};
    rawClusters.forEach((cluster, idx) => {
      obj[String(idx)] = cluster;
    });
    return obj;
  }
  return rawClusters || {};
}

function App() {
  const [noteInput, setNoteInput] = useState('');
  const [notes, setNotes] = useState<Note[]>([]);
  const [clusters, setClusters] = useState<ClusterData>({});
  const [clusterSummary, setClusterSummary] = useState<ClusterSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  
  const [clusteringMode, setClusteringMode] = useState<'auto' | 'manual'>('auto');
  const [maxK, setMaxK] = useState(10);
  const [manualK, setManualK] = useState(3);

  const fetchNotes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get<NotesResponse>(`${API_BASE_URL}/notes`);
      
      if (response.data.success) {
        setNotes(response.data.notes || []);
      } else {
        setError('Failed to fetch notes');
      }
    } catch (err: any) {
      console.error('Error fetching notes:', err);
      setError('Failed to fetch notes. Please check if the server is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchClusters = useCallback(async () => {
    try {
      setError(null);
      const params = new URLSearchParams();
      if (clusteringMode === 'auto') {
        params.append('auto_k', 'true');
        params.append('max_k', maxK.toString());
      } else {
        params.append('auto_k', 'false');
        params.append('k', manualK.toString());
      }

      const response = await axios.get<ClustersResponse>(`${API_BASE_URL}/clusters?${params}`);
      
      if (response.data.success) {
        setClusters(normalizeClusters(response.data.clusters));
      } else {
        setError('Failed to fetch clusters');
      }
    } catch (err: any) {
      console.error('Error fetching clusters:', err);
      if (err.response?.status === 500) {
        setError('Clustering failed. This might happen when there are too few notes. Try adding more notes.');
      } else {
        setError('Failed to fetch clusters. Please check if the server is running.');
      }
      setClusters({});
    }
  }, [clusteringMode, maxK, manualK]);

  const fetchClusterSummary = useCallback(async () => {
    try {
      setError(null);
      const params = new URLSearchParams();
      if (clusteringMode === 'auto') {
        params.append('auto_k', 'true');
        params.append('max_k', maxK.toString());
      } else {
        params.append('auto_k', 'false');
        params.append('k', manualK.toString());
      }

      const response = await axios.get<ClusterSummaryResponse>(`${API_BASE_URL}/cluster-summary?${params}`);
      
      if (response.data.success) {
        setClusterSummary(response.data.summary);
      } else {
        setError('Failed to fetch cluster summary');
      }
    } catch (err: any) {
      console.error('Error fetching cluster summary:', err);
      if (err.response?.status === 500) {
        setError('Cluster summary failed. This might happen when there are too few notes. Try adding more notes.');
      } else {
        setError('Failed to fetch cluster summary. Please check if the server is running.');
      }
      setClusterSummary(null);
    }
  }, [clusteringMode, maxK, manualK]);

  useEffect(() => {
    fetchClusterSummary();
  }, [fetchClusterSummary]);

  const handleSubmitNote = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!noteInput.trim()) {
      setError('Please enter a note');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);

      const response = await axios.post<ApiResponse<{ noteId: string; note: string }>>(`${API_BASE_URL}/note`, {
        note: noteInput.trim()
      });

      if (response.data.success) {
        setNoteInput('');
        setSuccessMessage('Note stored successfully!');
        await fetchNotes();
        await fetchClusters();
      } else {
        setError('Failed to store note');
      }
    } catch (err: any) {
      console.error('Error storing note:', err);
      setError('Failed to store note. Please check if the server is running.');
    } finally {
      setLoading(false);
    }
  };

  // Handle file selection for PDF upload
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type === 'application/pdf') {
        setSelectedFile(file);
        setError(null);
      } else {
        setError('Please select a PDF file');
        setSelectedFile(null);
      }
    }
  };

  // Upload PDF file
  const handleUploadPdf = async () => {
    if (!selectedFile) {
      setError('Please select a PDF file');
      return;
    }

    try {
      setUploadingPdf(true);
      setError(null);
      setSuccessMessage(null);

      const formData = new FormData();
      formData.append('pdf', selectedFile);

      const response = await axios.post<PdfUploadResponse>(`${API_BASE_URL}/upload-pdf`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        setSelectedFile(null);
        setSuccessMessage(`PDF uploaded successfully! Processed ${response.data.totalPages} pages.`);
        // Refresh notes and clusters
        await fetchNotes();
        await fetchClusters();
      } else {
        setError('Failed to upload PDF');
      }
    } catch (err: any) {
      console.error('Error uploading PDF:', err);
      if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else {
        setError('Failed to upload PDF. Please check if the server is running.');
      }
    } finally {
      setUploadingPdf(false);
    }
  };

  // Delete a note
  const handleDeleteNote = async (noteId: string) => {
    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);

      const response = await axios.delete<ApiResponse<{ noteId: string }>>(`${API_BASE_URL}/note/${noteId}`);

      if (response.data.success) {
        setSuccessMessage('Note deleted successfully!');
        await fetchNotes();
        
        try {
          await fetchClusters();
        } catch (clusteringError: any) {
          console.warn('Clustering failed after deletion:', clusteringError);
        }
      } else {
        setError('Failed to delete note');
      }
    } catch (err: any) {
      console.error('Error deleting note:', err);
      setError('Failed to delete note. Please check if the server is running.');
    } finally {
      setLoading(false);
    }
  };

  // Handle clustering controls
  const handleClusteringChange = useCallback(async () => {
    await fetchClusters();
  }, [fetchClusters]);

  useEffect(() => {
    fetchNotes();
    fetchClusters();
  }, [fetchNotes, fetchClusters]);

  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  return (
    <div className="App">
      <header className="App-header">
        <h1>🧠 Digital Second Brain</h1>
        <p>Store, organize, and cluster your notes and PDFs semantically</p>
      </header>

      <main className="App-main">
        {/* Error and Success Messages */}
        {error && (
          <div className="error-message">
            <span>❌ {error}</span>
            <button onClick={() => setError(null)} className="close-btn">×</button>
          </div>
        )}
        
        {successMessage && (
          <div className="success-message">
            <span>✅ {successMessage}</span>
            <button onClick={() => setSuccessMessage(null)} className="close-btn">×</button>
          </div>
        )}

        {/* Add Note Section */}
        <section className="add-note-section">
          <h2>📝 Add Note</h2>
          <form onSubmit={handleSubmitNote} className="note-form">
            <textarea
              value={noteInput}
              onChange={(e) => setNoteInput(e.target.value)}
              placeholder="Enter your note here..."
              className="note-input"
              rows={4}
              disabled={loading}
            />
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Storing...' : 'Store Note'}
            </button>
          </form>
        </section>

        {/* Upload PDF Section */}
        <section className="upload-pdf-section">
          <h2>📄 Upload PDF</h2>
          <div className="pdf-upload">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              className="file-input"
              disabled={uploadingPdf}
            />
            <button
              onClick={handleUploadPdf}
              disabled={!selectedFile || uploadingPdf}
              className="upload-btn"
            >
              {uploadingPdf ? 'Uploading...' : 'Upload PDF'}
            </button>
          </div>
        </section>

        <section className="clustering-controls">
          <h2>🔍 Clustering Controls</h2>
          <div className="controls">
            <div className="control-group">
              <label>
                <input
                  type="radio"
                  value="auto"
                  checked={clusteringMode === 'auto'}
                  onChange={(e) => setClusteringMode(e.target.value as 'auto' | 'manual')}
                />
                Auto-detect clusters
              </label>
              <label>
                <input
                  type="radio"
                  value="manual"
                  checked={clusteringMode === 'manual'}
                  onChange={(e) => setClusteringMode(e.target.value as 'auto' | 'manual')}
                />
                Manual clusters
              </label>
            </div>
            
            {clusteringMode === 'auto' && (
              <div className="control-group">
                <label>Max clusters:</label>
                <input
                  type="number"
                  min="2"
                  max="20"
                  value={maxK}
                  onChange={(e) => setMaxK(parseInt(e.target.value))}
                  className="number-input"
                />
              </div>
            )}
            
            {clusteringMode === 'manual' && (
              <div className="control-group">
                <label>Number of clusters:</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={manualK}
                  onChange={(e) => setManualK(parseInt(e.target.value))}
                  className="number-input"
                />
              </div>
            )}
            
            <button onClick={handleClusteringChange} className="cluster-btn">
              Update Clustering
            </button>
          </div>
        </section>

        <section className="cluster-summary">
          <h2>📊 Cluster Summary</h2>
          {clusterSummary ? (
            <div className="summary-stats">
              <p><strong>Total Notes:</strong> {clusterSummary.total_notes}</p>
              <p><strong>Number of Clusters:</strong> {clusterSummary.num_clusters}</p>
              <p><strong>Auto-determined:</strong> {clusterSummary.auto_determined_k ? 'Yes' : 'No'}</p>
            </div>
          ) : (
            <p>No cluster summary available</p>
          )}
        </section>

        <section className="notes-section">
          <h2>📝 All Notes ({notes.length})</h2>
          {loading ? (
            <p>Loading notes...</p>
          ) : notes.length === 0 ? (
            <p>No notes yet. Add your first note above!</p>
          ) : (
            <div className="notes-list">
              {notes.map((note) => (
                <div key={note._id} className="note-item">
                  <div className="note-content">
                    <p className="note-text">{note.note}</p>
                    {note.type === 'pdf' && (
                      <div className="pdf-info">
                        <span className="pdf-icon">📄</span>
                        <span>{note.filename}</span>
                        {note.total_pages && <span>({note.total_pages} pages)</span>}
                      </div>
                    )}
                    <div className="note-meta">
                      <span>Created: {new Date(note.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteNote(note._id)}
                    className="delete-btn"
                    disabled={loading}
                    title="Delete note"
                  >
                    {/* Trash can icon (Unicode) */}
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="clusters-section">
          <h2>🔍 Clusters</h2>
          {Object.keys(clusters).length === 0 ? (
            <p>No clusters available. Add more notes to see clustering in action!</p>
          ) : (
            <div className="clusters-list">
              {Object.entries(clusters).map(([clusterId, clusterNotes]) => (
                <div key={clusterId} className="cluster-item">
                  <h3>Cluster {clusterId} ({clusterNotes.length} notes)</h3>
                  <div className="cluster-notes">
                    {clusterNotes.map((note) => (
                      <div key={note._id} className="cluster-note">
                        <p className="note-text">{note.note}</p>
                        {note.type === 'pdf' && (
                          <div className="pdf-info">
                            <span className="pdf-icon">📄</span>
                            <span>{note.filename}</span>
                            {note.total_pages && <span>({note.total_pages} pages)</span>}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
