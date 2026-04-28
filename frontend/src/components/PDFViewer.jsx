import { useState, useRef, useEffect, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { X, ChevronLeft, ChevronRight, BookOpen, ZoomIn, ZoomOut } from 'lucide-react';

import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

/**
 * Side panel PDF viewer with page navigation and text highlighting.
 *
 * Props:
 *   documentId    — the uploaded document ID
 *   activeCitation — { page, section, text_snippet } or null
 *   onClose        — callback to close the viewer
 */
export default function PDFViewer({ documentId, activeCitation, onClose }) {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loadError, setLoadError] = useState(null);
  const containerRef = useRef(null);

  const pdfUrl = `/api/document/${documentId}/pdf`;

  // Navigate to the cited page when a citation is clicked
  useEffect(() => {
    if (activeCitation?.page) {
      setCurrentPage(activeCitation.page);
    }
  }, [activeCitation]);

  const onDocumentLoadSuccess = useCallback(({ numPages }) => {
    setNumPages(numPages);
    setLoadError(null);
  }, []);

  const onDocumentLoadError = useCallback((error) => {
    console.error('PDF load error:', error);
    setLoadError('Failed to load PDF');
  }, []);

  const goToPrev = () => setCurrentPage((p) => Math.max(1, p - 1));
  const goToNext = () => setCurrentPage((p) => Math.min(numPages || p, p + 1));
  const zoomIn = () => setScale((s) => Math.min(2.0, s + 0.15));
  const zoomOut = () => setScale((s) => Math.max(0.5, s - 0.15));

  // Highlight matching text in the PDF text layer
  const highlightText = useCallback(
    (textItem) => {
      if (!activeCitation?.text_snippet) return textItem.str;

      const snippet = activeCitation.text_snippet
        .replace(/\.\.\.$/,'') // Remove trailing ellipsis
        .trim();

      // Extract significant words (4+ chars) from the snippet for matching
      const words = snippet
        .split(/\s+/)
        .filter((w) => w.length >= 4)
        .map((w) => w.replace(/[^\w]/g, '').toLowerCase())
        .filter(Boolean);

      if (words.length === 0) return textItem.str;

      const text = textItem.str;
      const textLower = text.toLowerCase();

      // Check if any significant words match
      const hasMatch = words.some((word) => textLower.includes(word));

      if (hasMatch) {
        return `<mark class="pdf-highlight">${text}</mark>`;
      }

      return text;
    },
    [activeCitation]
  );

  return (
    <div className="h-full flex flex-col bg-bg-secondary border-l border-border animate-slide-in">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-border bg-bg-tertiary/50">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-text-primary">PDF Viewer</span>
          {numPages && (
            <span className="text-xs text-text-muted">
              ({numPages} pages)
            </span>
          )}
        </div>

        <button
          id="close-pdf-viewer"
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-colors"
          title="Close viewer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Active citation reference */}
      {activeCitation && (
        <div className="flex-shrink-0 mx-3 mt-3 p-3 rounded-lg bg-citation-bg border border-amber-500/20">
          <div className="flex items-center gap-1.5 mb-1.5">
            <BookOpen className="w-3 h-3 text-citation" />
            <span className="text-xs font-semibold text-citation">
              Referenced — Page {activeCitation.page}
              {activeCitation.section && `, Section: ${activeCitation.section}`}
            </span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
            {activeCitation.text_snippet}
          </p>
        </div>
      )}

      {/* Page navigation + zoom */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-1">
          <button
            onClick={goToPrev}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs text-text-secondary px-2 min-w-[80px] text-center">
            Page {currentPage} / {numPages || '...'}
          </span>
          <button
            onClick={goToNext}
            disabled={currentPage >= (numPages || 1)}
            className="p-1.5 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="p-1.5 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs text-text-muted px-1 min-w-[40px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            disabled={scale >= 2.0}
            className="p-1.5 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* PDF Page */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex justify-center p-4 bg-bg-primary/50"
      >
        {loadError ? (
          <div className="flex items-center justify-center h-full text-text-muted text-sm">
            {loadError}
          </div>
        ) : (
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex items-center justify-center h-64 text-text-muted text-sm">
                Loading PDF...
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              className="shadow-2xl rounded-lg overflow-hidden"
              customTextRenderer={highlightText}
              loading={
                <div className="flex items-center justify-center h-64 w-[400px] bg-bg-tertiary rounded-lg text-text-muted text-sm">
                  Rendering page {currentPage}...
                </div>
              }
            />
          </Document>
        )}
      </div>
    </div>
  );
}
