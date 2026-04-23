import { useState, useEffect } from 'react';
import { api, getImageUrl, setRuntimeOptions } from './services/api';
import './App.css';

const MAX_PROMPT_CHARS = 12000;

function estimateSecondsFromPrompt(prompt, size, numImages) {
  const words = prompt.trim().split(/\s+/).filter(Boolean).length;
  const hasQualityKeywords = /(cinematic|realistic|commercial|lighting|brand|hero|detailed|texture)/i.test(prompt);
  const sizePenalty = size === '16:9' ? 30 : size === '4:5' ? 22 : 18;
  const qualityBonus = words > 18 || hasQualityKeywords ? 55 : 30;
  const perImage = 42 * numImages;
  return Math.max(90, sizePenalty + qualityBonus + perImage);
}

function formatEta(seconds) {
  const safe = Math.max(0, Math.round(seconds));
  if (safe < 60) return `${safe}s`;
  const mins = Math.floor(safe / 60);
  const rem = safe % 60;
  return `${mins}m ${rem}s`;
}

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
  const [stage, setStage] = useState('idle');
  const [etaSeconds, setEtaSeconds] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [enhancedPreview, setEnhancedPreview] = useState('');
  const [useEnhancement, setUseEnhancement] = useState(true);
  const [generateImagesEnabled, setGenerateImagesEnabled] = useState(false);
  const [hfApiKey, setHfApiKey] = useState('');
  const [imageMode, setImageMode] = useState('online');

  useEffect(() => {
    checkHealth();
  }, []);

  useEffect(() => {
    if (!loading) return;
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [loading]);

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
    if (prompt.length > MAX_PROMPT_CHARS) {
      setError(`Prompt is too long. Keep it under ${MAX_PROMPT_CHARS} characters.`);
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setRuntimeOptions({ hfToken: hfApiKey, imageMode });
    setStage('Enhancing your prompt with LLM...');
    setElapsedSeconds(0);
    setEtaSeconds(estimateSecondsFromPrompt(prompt, size, generateImagesEnabled ? numImages : 0));
    setEnhancedPreview('');

    try {
      if (!generateImagesEnabled) {
        setStage('Generating text-only post...');
        const textOnly = await api.generateText(prompt, useEnhancement);
        setEnhancedPreview(textOnly.enhanced_prompt || '');
        setResult(textOnly);
        setStage('Completed');
        await loadHistory();
        return;
      }

      let workingPrompt = prompt;
      if (useEnhancement) {
        const enhanced = await api.enhancePrompt(prompt);
        workingPrompt = enhanced.enhanced_prompt;
        setEnhancedPreview(workingPrompt);
        const qualityEta = estimateSecondsFromPrompt(workingPrompt, size, generateImagesEnabled ? numImages : 0);
        setEtaSeconds(qualityEta);
      } else {
        setStage('Using your original prompt...');
      }

      setStage('Generating marketing caption...');
      const captionData = await api.generateCaption(workingPrompt);

      let images = [];
      if (generateImagesEnabled) {
        setStage('Generating real-world marketing images...');
        setEtaSeconds((prev) => Math.max(prev, 55 * numImages + (size === '16:9' ? 45 : 25)));
        const imageData = await api.generateImages(workingPrompt, size, numImages);
        images = imageData.images;
      } else {
        setStage('Text-only mode enabled. Skipping image generation...');
      }

      const savedGeneration = await api.saveGeneration({
        prompt,
        enhanced_prompt: useEnhancement ? workingPrompt : `Enhancement disabled. Using original prompt:\n${prompt}`,
        caption: captionData.caption,
        hashtags: captionData.hashtags,
        images,
      });

      setResult(savedGeneration);
      setStage('Completed');
      await loadHistory();
    } catch (err) {
      setError(err.message);
      setStage('Failed');
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

  function buildImageFallback(url) {
    const base = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000';
    return url.replace('/api/static/', `${base}/static/`);
  }

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
                  maxLength={MAX_PROMPT_CHARS}
                />
                <div className="char-counter">
                  {prompt.length}/{MAX_PROMPT_CHARS}
                </div>
              </div>

              {generateImagesEnabled && (
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
              )}

              {generateImagesEnabled && (
                <div className="form-row">
                <div className="form-group">
                  <label htmlFor="hfApiKey">Hugging Face API Key (optional)</label>
                  <input
                    id="hfApiKey"
                    type="password"
                    value={hfApiKey}
                    onChange={(e) => setHfApiKey(e.target.value)}
                    placeholder="hf_xxx..."
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="imageMode">Image Generation Mode</label>
                  <select
                    id="imageMode"
                    value={imageMode}
                    onChange={(e) => setImageMode(e.target.value)}
                  >
                    <option value="online">Online (HF provider)</option>
                    <option value="local">Local CPU (slower)</option>
                  </select>
                </div>
                </div>
              )}

              <div className="form-group">
                <label className="toggle-row">
                  <input
                    type="checkbox"
                    checked={useEnhancement}
                    onChange={(e) => setUseEnhancement(e.target.checked)}
                  />
                  <span>Use LLM prompt enhancement</span>
                </label>
              </div>

              <div className="form-group">
                <label className="toggle-row">
                  <input
                    type="checkbox"
                    checked={generateImagesEnabled}
                    onChange={(e) => setGenerateImagesEnabled(e.target.checked)}
                  />
                  <span>Generate images (disable for text-only output)</span>
                </label>
              </div>

              <button 
                className="btn-primary" 
                onClick={handleGenerate}
                disabled={loading}
              >
                {loading
                  ? 'Generating...'
                  : generateImagesEnabled
                    ? (useEnhancement ? 'Enhance Prompt + Generate Images' : 'Generate Images (No Enhancement)')
                    : (useEnhancement ? 'Enhance Prompt + Generate Text' : 'Generate Text (No Enhancement)')}
              </button>

              {loading && (
                <div className="progress-card">
                  <div className="progress-label">{stage}</div>
                  <div className="progress-meta">
                    <span>Elapsed: {formatEta(elapsedSeconds)}</span>
                    <span>ETA: {formatEta(Math.max(0, etaSeconds - elapsedSeconds))}</span>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${Math.min(100, (elapsedSeconds / Math.max(etaSeconds, 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              )}

              {enhancedPreview && !result && (
                <div className="result-section">
                  <h3>Enhanced Prompt (Live)</h3>
                  <p className="enhanced-prompt">{enhancedPreview}</p>
                </div>
              )}

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
                  <button
                    className="btn-secondary"
                    onClick={() => navigator.clipboard?.writeText(`${result.caption}\n\n${result.hashtags.join(' ')}`)}
                  >
                    Copy Post Text
                  </button>
                </div>

                <div className="result-section">
                  <h3>Hashtags</h3>
                  <div className="hashtags">
                    {result.hashtags.map((tag, i) => (
                      <span key={i} className="hashtag">{tag}</span>
                    ))}
                  </div>
                </div>

                {result.images.length > 0 && (
                <div className="result-section">
                  <h3>Generated Images</h3>
                  <div className="images-grid">
                    {result.images.map((img, i) => (
                      <div key={i} className="image-item">
                        {(() => {
                          const imageUrl = getImageUrl(img);
                          return (
                            <>
                        <img 
                          src={imageUrl}
                          alt={`Generated ${i + 1}`}
                          onError={(e) => {
                            e.target.src = buildImageFallback(imageUrl);
                          }}
                        />
                              <a
                                className="btn-download"
                                href={imageUrl}
                                download={`marketing-image-${i + 1}.png`}
                              >
                                Download
                              </a>
                            </>
                          );
                        })()}
                      </div>
                    ))}
                  </div>
                </div>
                )}

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
                          (() => {
                            const imageUrl = getImageUrl(img);
                            return (
                              <a
                                key={`${item.id}-img-${i}`}
                                href={imageUrl}
                                download={`history-image-${i + 1}.png`}
                                className="history-image-link"
                              >
                          <img 
                            src={imageUrl}
                            alt={`History ${i + 1}`}
                            className="history-thumb"
                            onError={(e) => {
                              e.target.src = buildImageFallback(imageUrl);
                            }}
                          />
                              </a>
                            );
                          })()
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
