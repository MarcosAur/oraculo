import { useState } from 'react'
import './MessageInput.css'

export default function MessageInput({ onSend, disabled }) {
  const [value, setValue] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    if (!value.trim() || disabled) return
    onSend(value)
    setValue('')
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  return (
    <form className="message-input" onSubmit={handleSubmit}>
      <textarea
        className="message-input__textarea"
        placeholder="Digite sua pergunta..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        disabled={disabled}
      />
      <button className="message-input__send" type="submit" disabled={disabled || !value.trim()}>
        Enviar
      </button>
    </form>
  )
}
