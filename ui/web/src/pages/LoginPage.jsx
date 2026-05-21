import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function LoginPage({ onSwitchToRegister }) {
  const { login, setError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [localError, setLocalError] = useState(null)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLocalError(null)
    setError(null)

    if (!email || !password) {
      setLocalError('Email and password are required.')
      return
    }

    setLoading(true)
    try {
      await login(email.trim(), password)
    } catch (err) {
      const message = err.message || 'Invalid login credentials.'
      setLocalError(message)
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 py-8 text-zinc-100">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900/95 p-8 shadow-xl shadow-black/20">
        <h1 className="text-2xl font-semibold text-zinc-100">Welcome back</h1>
        <p className="mt-2 text-sm text-zinc-500">Sign in to continue collecting training data.</p>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <InputField
            label="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            type="email"
          />
          <InputField
            label="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
          />

          {localError && <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{localError}</div>}

          <button
            type="submit"
            className="w-full rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-400 disabled:opacity-60"
            disabled={loading}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-zinc-500">
          <span>Don’t have an account?</span>{' '}
          <button type="button" className="font-semibold text-cyan-300 hover:text-cyan-100" onClick={onSwitchToRegister}>
            Create one
          </button>
        </div>
      </div>
    </div>
  )
}

function InputField({ label, value, onChange, type = 'text' }) {
  return (
    <label className="block text-sm font-medium text-zinc-300">
      <span>{label}</span>
      <input
        value={value}
        onChange={onChange}
        type={type}
        className="mt-2 block w-full rounded-2xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
      />
    </label>
  )
}
