import { BookOpen, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

/**
 * Single chat message bubble.
 *
 * Props:
 *   role            — 'user' | 'assistant'
 *   content         — message text (supports markdown)
 *   citations       — array of { page, section, text_snippet }
 *   isRefusal       — true if this is a refusal response
 *   onCitationClick — callback(citation) when a citation badge is clicked
 */
export default function ChatMessage({ role, content, citations = [], isRefusal = false, onCitationClick }) {
  const isUser = role === 'user';
  const displayContent = !isUser && citations.length > 0
    ? content.split(/\n\s*Sources\s*:/i)[0].trim()
    : content;

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pdf-reviewer-response.txt';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className={`flex w-full animate-fade-in-up ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`
          relative min-w-0 rounded-2xl px-5 py-3.5 break-words
          ${isUser
            ? 'max-w-[78%] bg-user-bubble text-white rounded-br-md'
            : isRefusal
              ? 'w-full max-w-[760px] glass border-error/20 rounded-bl-md'
              : 'w-full max-w-[760px] glass rounded-bl-md'
          }
        `}
      >
        {!isUser && (
          <button
            type="button"
            onClick={handleDownload}
            className="absolute right-3 top-2 inline-flex h-7 w-7 items-center justify-center rounded-lg text-text-muted opacity-70 hover:bg-bg-tertiary hover:text-text-primary hover:opacity-100 transition-colors"
            title="Download this response"
          >
            <Download className="w-3 h-3" />
          </button>
        )}

        {/* Message content */}
        <div className={`text-sm leading-relaxed ${isUser ? 'text-white' : 'text-text-primary pr-8'}`}>
          {isUser ? (
            <p>{content}</p>
          ) : (
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="text-text-primary leading-relaxed">{children}</li>,
                strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
                code: ({ children }) => (
                  <code className="px-1.5 py-0.5 bg-bg-tertiary rounded text-accent-light text-xs font-mono">
                    {children}
                  </code>
                ),
              }}
            >
              {displayContent}
            </ReactMarkdown>
          )}
        </div>

        {/* Citations */}
        {citations.length > 0 && !isRefusal && (
          <div className="mt-3 pt-3 border-t border-border">
            <div className="flex items-center gap-1.5 mb-2">
              <BookOpen className="w-3 h-3 text-citation" />
              <span className="text-xs font-medium text-citation">Sources — click to view in PDF</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {citations.map((cite, idx) => (
                <button
                  key={idx}
                  className="citation-badge"
                  title={cite.text_snippet}
                  onClick={() => onCitationClick && onCitationClick(cite)}
                >
                  Page {cite.page}
                  {cite.section && (
                    <span className="text-citation/70 ml-0.5">• {cite.section}</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
