import React, { useMemo, useState } from 'react'
import { AudioProvider } from './context/AudioContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import Dashboard from './pages/Dashboard'
import HistoryPage from './pages/HistoryPage'

function AppContent() {
  const [view, setView] = useState('dashboard')
  const { user } = useAuth()
  const [needsRegister, setNeedsRegister] = useState(false)

  if (!user) {
    return needsRegister ? (
      <RegisterPage onSwitchToLogin={() => setNeedsRegister(false)} />
    ) : (
      <LoginPage onSwitchToRegister={() => setNeedsRegister(true)} />
    )
  }

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-5">
        <div>
          <h1 className="text-base font-semibold tracking-[0.16em] text-zinc-100">AURALIS</h1>
          <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">User dashboard</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <button
            className={`rounded-md px-3 py-2 text-xs transition ${view === 'dashboard' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'}`}
            onClick={() => setView('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`rounded-md px-3 py-2 text-xs transition ${view === 'history' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'}`}
            onClick={() => setView('history')}
          >
            History
          </button>
        </div>
      </header>

      {view === 'dashboard' ? <Dashboard /> : <HistoryPage />}
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AudioProvider>
        <AppContent />
      </AudioProvider>
    </AuthProvider>
  )
}
