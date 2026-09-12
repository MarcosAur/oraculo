import { useState } from 'react'
import logo from '../assets/logo-oraculo.png'
import { ApiError } from '../api/client'
import './Login.css'

export default function Login({ onLogin, onRegister }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isRegister = mode === 'register'

  async function handleSubmit(event) {
    event.preventDefault()
    if (!email.trim() || !password || isSubmitting) return

    setError('')
    setIsSubmitting(true)
    try {
      if (isRegister) {
        await onRegister(email.trim(), password)
      } else {
        await onLogin(email.trim(), password)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível conectar ao servidor.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function toggleMode() {
    setError('')
    setMode(isRegister ? 'login' : 'register')
  }

  return (
    <div className="login">
      <div className="login__bg" aria-hidden="true">
        <div className="login__bg-glow" />
      </div>

      <form className="login__card" onSubmit={handleSubmit}>
        <div className="login__brand">
          <img className="login__logo" src={logo} alt="Oráculo" />
          <h1 className="login__title">Oráculo</h1>
        </div>
        <p className="login__subtitle">
          {isRegister ? 'Crie sua conta para começar' : 'Entre para continuar sua conversa'}
        </p>

        <label className="login__label" htmlFor="login-email">
          E-mail
        </label>
        <input
          id="login-email"
          className="login__input"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="voce@exemplo.com"
          required
        />

        <label className="login__label" htmlFor="login-password">
          Senha
        </label>
        <input
          id="login-password"
          className="login__input"
          type="password"
          autoComplete={isRegister ? 'new-password' : 'current-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          minLength={isRegister ? 6 : undefined}
          required
        />

        {error && <p className="login__error">{error}</p>}

        <button className="login__submit" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Aguarde...' : isRegister ? 'Criar conta' : 'Entrar'}
        </button>

        <button className="login__toggle" type="button" onClick={toggleMode}>
          {isRegister ? 'Já tem uma conta? Entrar' : 'Ainda não tem conta? Criar conta'}
        </button>
      </form>
    </div>
  )
}
