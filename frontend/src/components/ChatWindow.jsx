import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'
import MessageInput from './MessageInput'
import './ChatWindow.css'

export default function ChatWindow({ conversation, isSending, onSend }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages.length, isSending])

  if (!conversation) {
    return (
      <div className="chat-window chat-window--empty">
        <div className="chat-window__bg" aria-hidden="true">
          <div className="chat-window__bg-glow" />
          <div className="chat-window__bg-rays" />
          <div className="chat-window__bg-vignette" />
        </div>
        <p className="chat-window__hint">Selecione ou crie uma conversa</p>
      </div>
    )
  }

  return (
    <div className="chat-window">
      <div className="chat-window__bg" aria-hidden="true">
        <div className="chat-window__bg-glow" />
        <div className="chat-window__bg-rays" />
        <div className="chat-window__bg-vignette" />
      </div>

      <header className="chat-window__header">
        <h1 className="chat-window__title">{conversation.title}</h1>
      </header>

      <div className="chat-window__messages">
        {conversation.messages.length === 0 && (
          <p className="chat-window__hint">Faça uma pergunta para começar a conversa.</p>
        )}
        {conversation.messages.map((message) => (
          <MessageBubble key={message.id} {...message} />
        ))}
        {isSending && <TypingIndicator />}
        <div ref={endRef} />
      </div>

      <MessageInput onSend={onSend} disabled={isSending} />
    </div>
  )
}
