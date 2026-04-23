const API_BASE = '/api';
let runtimeOptions = {
  hfToken: '',
  imageMode: 'online',
};

export function setRuntimeOptions({ hfToken, imageMode }) {
  runtimeOptions = {
    hfToken: hfToken ?? runtimeOptions.hfToken,
    imageMode: imageMode ?? runtimeOptions.imageMode,
  };
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
  };
  if (runtimeOptions.hfToken?.trim()) {
    headers['x-hf-token'] = runtimeOptions.hfToken.trim();
  }
  if (runtimeOptions.imageMode) {
    headers['x-image-mode'] = runtimeOptions.imageMode;
  }
  const config = {
    headers,
    ...options,
  };

  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, config);
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    if (!isJson) {
      if (response.status === 502 || response.status === 503 || response.status === 504) {
        throw new Error('Generation timed out at proxy while backend is still processing. On local CPU this may take 5-15 minutes for first run. Try 1 image first or wait longer.');
      }
      throw new Error(`Request failed with status ${response.status}`);
    }
    let detail = `Request failed with status ${response.status}`;
    if (typeof payload?.detail === 'string') {
      detail = payload.detail;
    } else if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
      const first = payload.detail[0];
      if (first?.msg) {
        detail = first.msg;
        if (Array.isArray(first.loc) && first.loc.length > 0) {
          detail = `${first.loc.join('.')} - ${first.msg}`;
        }
      }
    }
    throw new Error(detail);
  }

  return payload;
}

export const api = {
  health: () => request('/health'),
  
  diagnostics: () => request('/diagnostics/huggingface'),
  
  enhancePrompt: (prompt) => 
    request('/enhance-prompt', { method: 'POST', body: { prompt } }),
  
  generateCaption: (prompt) => 
    request('/generate-caption', { method: 'POST', body: { prompt } }),
  
  generateImages: (prompt, size = '1:1', numImages = 3) => 
    request('/generate-images', { method: 'POST', body: { prompt, size, num_images: numImages } }),
  
  generatePost: (prompt, size = '1:1', numImages = 3) => 
    request('/generate-post', { method: 'POST', body: { prompt, size, num_images: numImages } }),

  generateText: (prompt, useEnhancement = true) =>
    request('/generate-text', { method: 'POST', body: { prompt, use_enhancement: useEnhancement } }),

  saveGeneration: (payload) =>
    request('/save-generation', { method: 'POST', body: payload }),
  
  getHistory: () => request('/history'),
  
  deleteGeneration: (id) => 
    request(`/delete/${id}`, { method: 'DELETE' }),
};

export function getImageUrl(relativePath) {
  const normalized = String(relativePath || '').replace(/\\/g, '/');
  const withoutOutputsPrefix = normalized.startsWith('outputs/')
    ? normalized.slice('outputs/'.length)
    : normalized;
  return `/api/static/${withoutOutputsPrefix}`;
}
