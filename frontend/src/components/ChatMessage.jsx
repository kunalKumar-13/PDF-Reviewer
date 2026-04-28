import { BookOpen } from 'lucide-react';
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

  return (
    <div
      className={`flex w-full animate-fade-in-up ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`
          max-w-[80%] rounded-2xl px-5 py-3.5
          ${isUser
            ? 'bg-user-bubble text-white rounded-br-md'
            : isRefusal
              ? 'glass border-error/20 rounded-bl-md'
              : 'glass rounded-bl-md'
          }
        `}
      >
        {/* Message content */}
        <div className={`text-sm leading-relaxed ${isUser ? 'text-white' : 'text-text-primary'}`}>
          {isUser ? (
            <p>{content}</p>
          ) : (
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="text-text-primary">{children}</li>,
                strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
                code: ({ children }) => (
                  <code className="px-1.5 py-0.5 bg-bg-tertiary rounded text-accent-light text-xs font-mono">
                    {children}
                  </code>
                ),
              }}
            >
              {content}
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
