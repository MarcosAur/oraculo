import { useCallback, useEffect, useState } from 'react'
import { askQuestion, ApiError } from '../api/client'

const STORAGE_KEY = 'oraculo.conversations.v1'

function createId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function createConversation() {
  const id = createId()
  return {
    id,
    title: 'Nova conversa',
    createdAt: Date.now(),
    messages: [],
  }
}

function loadInitialState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed.conversations) && parsed.conversations.length > 0) {
        return parsed
      }
    }
  } catch (error) {
    console.warn('Não foi possível carregar o histórico salvo:', error)
  }

  const first = createConversation()
  return { conversations: [first], activeId: first.id }
}

export function useConversations(token, onUnauthorized) {
  const [{ conversations, activeId }, setState] = useState(loadInitialState)
  const [isSending, setIsSending] = useState(false)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ conversations, activeId }))
  }, [conversations, activeId])

  const activeConversation = conversations.find((c) => c.id === activeId) ?? conversations[0]

  const startNewConversation = useCallback(() => {
    setState((prev) => {
      const fresh = createConversation()
      return { conversations: [fresh, ...prev.conversations], activeId: fresh.id }
    })
  }, [])

  const selectConversation = useCallback((id) => {
    setState((prev) => ({ ...prev, activeId: id }))
  }, [])

  const deleteConversation = useCallback((id) => {
    setState((prev) => {
      const remaining = prev.conversations.filter((c) => c.id !== id)
      if (remaining.length === 0) {
        const fresh = createConversation()
        return { conversations: [fresh], activeId: fresh.id }
      }
      const nextActiveId = prev.activeId === id ? remaining[0].id : prev.activeId
      return { conversations: remaining, activeId: nextActiveId }
    })
  }, [])

  const sendQuestion = useCallback(async (question) => {
    const trimmed = question.trim()
    if (!trimmed || isSending) return

    const conversationId = activeId
    const userMessage = { id: createId(), role: 'user', content: trimmed, timestamp: Date.now() }

    setState((prev) => ({
      ...prev,
      conversations: prev.conversations.map((c) =>
        c.id === conversationId
          ? {
              ...c,
              title: c.messages.length === 0 ? trimmed.slice(0, 40) : c.title,
              messages: [...c.messages, userMessage],
            }
          : c,
      ),
    }))

    setIsSending(true)
    try {
      const { answer, sources } = await askQuestion(token, trimmed)
      const assistantMessage = {
        id: createId(),
        role: 'assistant',
        content: answer,
        timestamp: Date.now(),
        sources,
      }

      setState((prev) => ({
        ...prev,
        conversations: prev.conversations.map((c) =>
          c.id === conversationId ? { ...c, messages: [...c.messages, assistantMessage] } : c,
        ),
      }))
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized?.()
        return
      }

      const errorMessage = {
        id: createId(),
        role: 'assistant',
        content: `Não foi possível obter a resposta: ${error.message}`,
        timestamp: Date.now(),
      }

      setState((prev) => ({
        ...prev,
        conversations: prev.conversations.map((c) =>
          c.id === conversationId ? { ...c, messages: [...c.messages, errorMessage] } : c,
        ),
      }))
    } finally {
      setIsSending(false)
    }
  }, [activeId, isSending, token, onUnauthorized])

  return {
    conversations,
    activeConversation,
    isSending,
    startNewConversation,
    selectConversation,
    deleteConversation,
    sendQuestion,
  }
}
