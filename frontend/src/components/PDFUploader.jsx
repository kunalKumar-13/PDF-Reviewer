import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react';

/**
 * PDF upload component with drag-and-drop support.
 *
 * Props:
 *   onUpload(file)  — called when a valid PDF is dropped/selected
 *   uploadState     — 'idle' | 'uploading' | 'success' | 'error'
 *   uploadProgress  — 0-100 progress percentage
 *   uploadMessage   — status message to display
 *   documentInfo    — { total_pages, total_chunks } after success
 */
export default function PDFUploader({
  onUpload,
  uploadState = 'idle',
  uploadProgress = 0,
  uploadMessage = '',
  documentInfo = null,
  disabled = false,
  disabledMessage = '',
}) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      if (!disabled && acceptedFiles.length > 0) {
        onUpload(acceptedFiles[0]);
      }
    },
    [disabled, onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: disabled || uploadState === 'uploading',
  });

  const isProcessing = uploadState === 'uploading';
  const isSuccess = uploadState === 'success';
  const isError = uploadState === 'error';
  const isDisabled = disabled && !isProcessing;

  return (
    <div className="w-full max-w-2xl mx-auto animate-fade-in-up">
      <div
        {...getRootProps()}
        id="pdf-upload-dropzone"
        className={`
          relative rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer
          transition-all duration-300 ease-out
          ${isDragActive
            ? 'border-accent bg-accent-glow scale-[1.02]'
            : isSuccess
              ? 'border-success/40 bg-success/5'
              : isError
                ? 'border-error/40 bg-error/5'
                : 'border-border hover:border-border-hover hover:bg-bg-tertiary/50'
          }
          ${isProcessing || isDisabled ? 'pointer-events-none opacity-80' : ''}
        `}
      >
        <input {...getInputProps()} id="pdf-file-input" />

        {/* Icon */}
        <div className="flex justify-center mb-4">
          {isProcessing ? (
            <Loader className="w-12 h-12 text-accent animate-spin" />
          ) : isDisabled ? (
            <Loader className="w-12 h-12 text-accent animate-spin" />
          ) : isSuccess ? (
            <CheckCircle className="w-12 h-12 text-success" />
          ) : isError ? (
            <AlertCircle className="w-12 h-12 text-error" />
          ) : isDragActive ? (
            <Upload className="w-12 h-12 text-accent animate-bounce" />
          ) : (
            <FileText className="w-12 h-12 text-text-secondary" />
          )}
        </div>

        {/* Main text */}
        <p className="text-lg font-medium text-text-primary mb-1">
          {isProcessing
            ? 'Processing your PDF...'
            : isDisabled
              ? 'Waking backend...'
            : isSuccess
              ? 'PDF Ready!'
              : isError
                ? 'Upload Failed'
                : isDragActive
                  ? 'Drop your PDF here'
                  : 'Drag & drop a PDF, or click to browse'}
        </p>

        {/* Sub text */}
        <p className="text-sm text-text-muted">
          {isProcessing
            ? uploadMessage || `Uploading... ${uploadProgress}%`
            : isDisabled
              ? disabledMessage || 'Server is starting. Upload will be available shortly.'
            : isSuccess && documentInfo
              ? `${documentInfo.total_pages} pages • ${documentInfo.total_chunks} chunks indexed`
              : isError
                ? uploadMessage || 'Something went wrong. Try again.'
                : `Maximum file size: 50MB`}
        </p>

        {/* Progress bar */}
        {isProcessing && (
          <div className="mt-4 mx-auto max-w-xs">
            <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-accent to-accent-light rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Success: option to upload another */}
        {isSuccess && (
          <button
            className="mt-4 text-xs text-accent hover:text-accent-light underline underline-offset-2 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              // re-trigger the dropzone
            }}
          >
            Upload a different PDF
          </button>
        )}
      </div>
    </div>
  );
}
