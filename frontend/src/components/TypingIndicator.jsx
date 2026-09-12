import './TypingIndicator.css'

export default function TypingIndicator() {
  return (
    <div className="message-row">
      <div className="message-bubble message-bubble--assistant typing-indicator">
        <span className="typing-indicator__dot" />
        <span className="typing-indicator__dot" />
        <span className="typing-indicator__dot" />
      </div>
    </div>
  )
}
