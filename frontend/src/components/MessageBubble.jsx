import './MessageBubble.css'

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export default function MessageBubble({ role, content, timestamp, sources }) {
  const isUser = role === 'user'
  const hasSources = Array.isArray(sources) && sources.length > 0

  return (
    <div className={'message-row' + (isUser ? ' message-row--user' : '')}>
      <div className={'message-bubble' + (isUser ? ' message-bubble--user' : ' message-bubble--assistant')}>
        <p className="message-bubble__content">{content}</p>
        {hasSources && (
          <ul className="message-bubble__sources">
            {sources.map((source, index) => (
              <li key={index}>{source.source_path}</li>
            ))}
          </ul>
        )}
        <span className="message-bubble__time">{formatTime(timestamp)}</span>
      </div>
    </div>
  )
}
