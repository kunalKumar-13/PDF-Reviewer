/**
 * Typing indicator — animated dots shown while the agent is processing.
 */
export default function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in-up">
      <div className="glass rounded-2xl rounded-bl-md px-5 py-3.5">
        <div className="flex items-center gap-1.5">
          <span className="typing-dot w-2 h-2 bg-accent rounded-full inline-block" />
          <span className="typing-dot w-2 h-2 bg-accent rounded-full inline-block" />
          <span className="typing-dot w-2 h-2 bg-accent rounded-full inline-block" />
          <span className="text-xs text-text-muted ml-2">Thinking...</span>
        </div>
      </div>
    </div>
  );
}
