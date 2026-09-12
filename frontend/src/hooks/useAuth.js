import { useCallback, useState } from 'react'
import { login as apiLogin, register as apiRegister } from '../api/client'

const TOKEN_KEY = 'oraculo.auth.token'
const EMAIL_KEY = 'oraculo.auth.email'

export function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [email, setEmail] = useState(() => localStorage.getItem(EMAIL_KEY))

  const login = useCallback(async (loginEmail, password) => {
    const data = await apiLogin(loginEmail, password)
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(EMAIL_KEY, loginEmail)
    setToken(data.access_token)
    setEmail(loginEmail)
  }, [])

  const register = useCallback(async (registerEmail, password) => {
    await apiRegister(registerEmail, password)
    await login(registerEmail, password)
  }, [login])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
    setToken(null)
    setEmail(null)
  }, [])

  return { token, email, isAuthenticated: Boolean(token), login, register, logout }
}
