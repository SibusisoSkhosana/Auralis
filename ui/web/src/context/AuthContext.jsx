import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiClient, setAuthToken, AUTH_STORAGE, AUTH_DATA_STORAGE } from '../api/client'

const AuthContext = createContext(null)
const STORAGE_KEY = AUTH_DATA_STORAGE

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (parsed?.token && parsed?.user) {
          setToken(parsed.token)
          setUser(parsed.user)
          setAuthToken(parsed.token)
          localStorage.setItem(AUTH_STORAGE, parsed.token)
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY)
        localStorage.removeItem(AUTH_STORAGE)
      }
    }
    setLoading(false)
  }, [])

  const persistAuth = (authUser, authToken) => {
    setToken(authToken)
    setUser(authUser)
    setAuthToken(authToken)
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: authUser, token: authToken }))
    localStorage.setItem(AUTH_STORAGE, authToken)
  }

  const login = async (email, password) => {
    const response = await apiClient.login({ email, password })
    persistAuth(response.user, response.access_token)
    return response
  }

  const register = async (email, password, consent) => {
    const response = await apiClient.register({ email, password, consent_to_training: consent })
    persistAuth(response.user, response.access_token)
    return response
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    setError(null)
    setAuthToken(null)
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(AUTH_STORAGE)
  }

  const value = useMemo(
    () => ({ user, token, loading, error, login, register, logout, setError }),
    [user, token, loading, error]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
