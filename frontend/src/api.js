import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';
const api = axios.create({
  baseURL: API_BASE,
  timeout: 180000,
});

export function getPDFUrl(documentId) {
  return `${API_BASE}/document/${documentId}/pdf`;
}

/**
 * Upload a PDF file for processing.
 * @param {File} file - The PDF file to upload.
 * @param {function} onProgress - Optional progress callback (0-100).
 * @returns {Promise<object>} Upload response with document_id.
 */
export async function uploadPDF(file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    },
  });

  return response.data;
}

/**
 * Send a chat question about the uploaded PDF.
 * @param {string} question - The user's question.
 * @param {string} documentId - The document to query.
 * @param {string|null} sessionId - Optional session ID for continuity.
 * @returns {Promise<object>} Chat response with answer and citations.
 */
export async function sendMessage(question, documentId, sessionId = null) {
  const response = await api.post('/chat', {
    question,
    document_id: documentId,
    session_id: sessionId,
  });

  return response.data;
}

/**
 * Health check.
 * @returns {Promise<object>}
 */
export async function healthCheck() {
  const response = await api.get('/health', {
    params: { t: Date.now() },
    timeout: 30000,
  });
  return response.data;
}
