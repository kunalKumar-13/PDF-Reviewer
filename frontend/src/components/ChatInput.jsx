import { useState, useRef } from 'react';
import { Send } from 'lucide-react';

/**
 * Chat input bar with send button.
 *
 * Props:
 *   onSend(message) — called when the user submits a message
 *   disabled        — true when chat is not available
 *   isLoading       — true while waiting for agent response
 */
export default function ChatInput({ onSend, disabled = false, isLoading = false }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed && !disabled && !isLoading) {
      onSend(trimmed);
      setInput('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e) => {
    setInput(e.target.value);
    // Auto-resize textarea
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div
        className={`
          glass rounded-2xl flex items-end gap-3 px-4 py-3
          transition-all duration-200
          ${disabled ? 'opacity-50' : 'focus-within:border-accent/40'}
        `}
      >
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled
              ? 'Upload a PDF to start chatting...'
              : 'Ask a question about your PDF...'
          }
          disabled={disabled || isLoading}
          rows={1}
          className="
            flex-1 bg-transparent text-text-primary placeholder-text-muted
            text-sm resize-none outline-none min-h-[24px] max-h-[160px]
            leading-relaxed
          "
        />

        <button
          type="submit"
          id="send-button"
          disabled={disabled || isLoading || !input.trim()}
          className={`
            flex-shrink-0 p-2.5 rounded-xl transition-all duration-200
            ${!disabled && !isLoading && input.trim()
              ? 'bg-accent hover:bg-accent-light text-white shadow-lg shadow-accent/25 hover:shadow-accent/40 cursor-pointer'
              : 'bg-bg-tertiary text-text-muted cursor-not-allowed'
            }
          `}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}
