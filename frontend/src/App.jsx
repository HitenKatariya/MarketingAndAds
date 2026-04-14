import { useState, useEffect } from 'react';
import { api, getImageUrl } from './services/api';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('generate');
  const [prompt, setPrompt] = useState('');
  const [size, setSize] = useState('1:1');
  const [numImages, setNumImages] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [health, setHealth] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    checkHealth();
  }, []);

  async function checkHealth() {
    try {
      const data = await api.health();
      setHealth(data);
    } catch (err) {
      setHealth({ status: 'error', message: err.message });
    }
  }

  async function handleGenerate() {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.generatePost(prompt, size, numImages);
      setResult(data);
      await loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
    setHistoryLoading(true);
    try {
      const data = await api.getHistory();
      setHistory(data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleDelete(id) {
    try {
      await api.deleteGeneration(id);
      await loadHistory();
      if (result?.id === id) {
        setResult(null);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab]);

  return (
    <div className="app">
      <header className="header">
        <h1>AI Social Media Post Generator</h1>
        <div className="status">
          {health ? (
            health.status === 'ok' ? (
              <span className="status-ok">
                API: {health.mode} | HF: {health.hf_configured}
              </span>
            ) : (
              <span className="status-error">API Error</span>
            )
          ) : (
            <span className="status-loading">Checking API...</span>
          )}
        </div>
      </header>

      <nav className="nav">
        <button 
          className={`nav-btn ${activeTab === 'generate' ? 'active' : ''}`}
          onClick={() => setActiveTab('generate')}
        >
          Generate
        </button>
        <button 
          className={`nav-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          History
        </button>
      </nav>

      <main className="main">
        {activeTab === 'generate' ? (
          <div className="generate-section">
            <div className="form-card">
              <h2>Create New Post</h2>
              
              <div className="form-group">
                <label htmlFor="prompt">Your Idea</label>
                <textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g., Red chilly pizza with oregano spray for my cafe"
                  rows={4}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="size">Image Size</label>
                  <select id="size" value={size} onChange={(e) => setSize(e.target.value)}>
                    <option value="1:1">Square (1:1)</option>
                    <option value="4:5">Portrait (4:5)</option>
                    <option value="16:9">Landscape (16:9)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="numImages">Number of Images</label>
                  <select 
                    id="numImages" 
                    value={numImages} 
                    onChange={(e) => setNumImages(Number(e.target.value))}
                  >
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                    <option value={4}>4</option>
                  </select>
                </div>
              </div>

              <button 
                className="btn-primary" 
                onClick={handleGenerate}
                disabled={loading}
              >
                {loading ? 'Generating...' : 'Generate Post'}
              </button>

              {error && <div className="error-msg">{error}</div>}
            </div>

            {result && (
              <div className="result-card">
                <h2>Generated Post</h2>
                
                <div className="result-section">
                  <h3>Enhanced Prompt</h3>
                  <p className="enhanced-prompt">{result.enhanced_prompt}</p>
                </div>

                <div className="result-section">
                  <h3>Caption</h3>
                  <p className="caption">{result.caption}</p>
                </div>

                <div className="result-section">
                  <h3>Hashtags</h3>
                  <div className="hashtags">
                    {result.hashtags.map((tag, i) => (
                      <span key={i} className="hashtag">{tag}</span>
                    ))}
                  </div>
                </div>

                <div className="result-section">
                  <h3>Generated Images</h3>
                  <div className="images-grid">
                    {result.images.map((img, i) => (
                      <div key={i} className="image-item">
                        <img 
                          src={`/api/static/${img.split('/').pop()}`}
                          alt={`Generated ${i + 1}`}
                          onError={(e) => {
                            e.target.src = `http://127.0.0.1:8000/static/${img.split('/').pop()}`;
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="result-meta">
                  ID: {result.id} | Created: {new Date(result.created_at).toLocaleString()}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="history-section">
            <div className="history-header">
              <h2>Generation History</h2>
              <button className="btn-secondary" onClick={loadHistory} disabled={historyLoading}>
                {historyLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            {history.length === 0 ? (
              <p className="empty-state">No generations yet. Create your first post!</p>
            ) : (
              <div className="history-list">
                {history.map((item) => (
                  <div key={item.id} className="history-item">
                    <div className="history-item-header">
                      <span className="history-date">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                      <button 
                        className="btn-delete"
                        onClick={() => handleDelete(item.id)}
                      >
                        Delete
                      </button>
                    </div>
                    
                    <div className="history-item-content">
                      <p><strong>Original:</strong> {item.prompt}</p>
                      <p><strong>Enhanced:</strong> {item.enhanced_prompt}</p>
                      <p><strong>Caption:</strong> {item.caption}</p>
                      <div className="hashtags">
                        {item.hashtags.map((tag, i) => (
                          <span key={i} className="hashtag">{tag}</span>
                        ))}
                      </div>
                    </div>

                    {item.images.length > 0 && (
                      <div className="history-images">
                        {item.images.map((img, i) => (
                          <img 
                            key={i}
                            src={`/api/static/${img.split('/').pop()}`}
                            alt={`History ${i + 1}`}
                            className="history-thumb"
                            onError={(e) => {
                              e.target.src = `http://127.0.0.1:8000/static/${img.split('/').pop()}`;
                            }}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
