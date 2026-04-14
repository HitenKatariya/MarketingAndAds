const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, config);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || `Request failed with status ${response.status}`);
    }
    
    return data;
  } catch (error) {
    throw error;
  }
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
  
  getHistory: () => request('/history'),
  
  deleteGeneration: (id) => 
    request(`/delete/${id}`, { method: 'DELETE' }),
};

export function getImageUrl(relativePath) {
  return `/api/static/${relativePath.split('/').pop()}`;
}
