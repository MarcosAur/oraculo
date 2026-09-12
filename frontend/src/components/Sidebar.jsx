import logo from '../assets/logo-oraculo.png'
import './Sidebar.css'

function formatDate(timestamp) {
  return new Date(timestamp).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

export default function Sidebar({ conversations, activeId, email, onSelect, onNew, onDelete, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <img className="sidebar__logo" src={logo} alt="Oráculo" />
        <span className="sidebar__brand-name">Oráculo</span>
      </div>

      <button className="sidebar__new-btn" onClick={onNew}>
        + Nova conversa
      </button>

      <ul className="sidebar__list">
        {conversations.map((conversation) => (
          <li
            key={conversation.id}
            className={
              'sidebar__item' + (conversation.id === activeId ? ' sidebar__item--active' : '')
            }
          >
            <button className="sidebar__item-btn" onClick={() => onSelect(conversation.id)}>
              <span className="sidebar__item-title">{conversation.title}</span>
              <span className="sidebar__item-date">{formatDate(conversation.createdAt)}</span>
            </button>
            <button
              className="sidebar__item-delete"
              title="Excluir conversa"
              onClick={() => onDelete(conversation.id)}
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      <div className="sidebar__footer">
        {email && <span className="sidebar__email" title={email}>{email}</span>}
        <button className="sidebar__logout" onClick={onLogout}>
          Sair
        </button>
      </div>
    </aside>
  )
}
