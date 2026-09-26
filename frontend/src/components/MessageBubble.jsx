import './MessageBubble.css'

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

const MODE_LABELS = {
  bm25: 'palavras-chave',
  vector: 'semântica',
  hybrid: 'híbrida',
}

function formatScore(score, retrieverMode) {
  if (!Number.isFinite(score)) return null
  if (retrieverMode === 'vector') {
    return `Similaridade: ${(score * 100).toFixed(0)}%`
  }
  return `Score: ${score.toFixed(retrieverMode === 'hybrid' ? 4 : 2)}`
}

export default function MessageBubble({ role, content, timestamp, sources, retrieverMode }) {
  const isUser = role === 'user'
  const hasSources = Array.isArray(sources) && sources.length > 0

  return (
    <div className={'message-row' + (isUser ? ' message-row--user' : '')}>
      <div className={'message-bubble' + (isUser ? ' message-bubble--user' : ' message-bubble--assistant')}>
        <p className="message-bubble__content">{content}</p>
        {hasSources && (
          <div className="message-bubble__source-block">
            <span className="message-bubble__source-title">
              Fontes{retrieverMode ? ` · busca ${MODE_LABELS[retrieverMode]}` : ''}
            </span>
            <ul className="message-bubble__sources">
              {sources.map((source, index) => {
                const score = formatScore(source.score, retrieverMode)
                const samePage = source.page_start === source.page_end
                const pages = samePage
                  ? `p. ${source.page_start}`
                  : `p. ${source.page_start}-${source.page_end}`
                return (
                  <li key={`${source.source_path}-${source.page_start}-${index}`} className="message-bubble__source-item">
                    <span className="source-path">{source.source_path}</span>
                    <span className="source-meta">
                      ({pages}{score ? ` | ${score}` : ''})
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}
        <span className="message-bubble__time">{formatTime(timestamp)}</span>
      </div>
    </div>
  )
}
