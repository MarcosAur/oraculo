import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import Login from './components/Login'
import { useAuth } from './hooks/useAuth'
import { useConversations } from './hooks/useConversations'
import './App.css'

export default function App() {
  const { token, email, isAuthenticated, login, register, logout } = useAuth()
  const {
    conversations,
    activeConversation,
    isSending,
    startNewConversation,
    selectConversation,
    deleteConversation,
    sendQuestion,
  } = useConversations(token, logout)

  if (!isAuthenticated) {
    return <Login onLogin={login} onRegister={register} />
  }

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeConversation?.id}
        email={email}
        onSelect={selectConversation}
        onNew={startNewConversation}
        onDelete={deleteConversation}
        onLogout={logout}
      />
      <ChatWindow conversation={activeConversation} isSending={isSending} onSend={sendQuestion} />
    </div>
  )
}
