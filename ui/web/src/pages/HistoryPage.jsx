import React, { useEffect, useState } from 'react'
import { apiClient } from '../api/client'

export default function HistoryPage() {
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let canceled = false
    setLoading(true)
    apiClient.getHistory()
      .then((data) => {
        if (!canceled) {
          setHistory(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!canceled) {
          setError(err.message || 'Failed to load history.')
          setLoading(false)
        }
      })

    return () => {
      canceled = true
    }
  }, [])

  if (loading) {
    return <div className="p-10 text-sm text-zinc-400">Loading history…</div>
  }

  if (error) {
    return <div className="p-10 rounded-xl border border-red-500/20 bg-red-500/10 text-red-200">{error}</div>
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#0b0d10]">
      <div className="space-y-6 p-6">
        <section className="rounded-3xl border border-zinc-800 bg-zinc-950/90 p-6 shadow-inner shadow-black/20">
          <h2 className="text-lg font-semibold text-zinc-100">Upload history</h2>
          <p className="mt-2 text-sm text-zinc-500">Tracked uploads, processing sessions, and persisted audio metadata.</p>
          <div className="mt-5 space-y-3">
            {history.uploads.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 text-sm text-zinc-500">No uploads yet.</div>
            ) : (
              history.uploads.map((upload) => (
                <div key={upload.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 text-sm text-zinc-200">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-medium text-zinc-100">{upload.original_name}</p>
                      <p className="text-xs text-zinc-500">Uploaded {upload.uploaded_at}</p>
                    </div>
                    <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">{upload.status}</div>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    <div>
                      <p className="text-xs text-zinc-500">Stored path</p>
                      <p className="break-all text-sm text-zinc-300">{upload.path}</p>
                    </div>
                    <div>
                      <p className="text-xs text-zinc-500">Size</p>
                      <p className="text-sm text-zinc-300">{formatBytes(upload.size)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-zinc-500">Content type</p>
                      <p className="text-sm text-zinc-300">{upload.content_type || 'n/a'}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-zinc-800 bg-zinc-950/90 p-6 shadow-inner shadow-black/20">
          <h2 className="text-lg font-semibold text-zinc-100">Feedback timeline</h2>
          <p className="mt-2 text-sm text-zinc-500">See which presets were submitted and how training records are stored.</p>
          <div className="mt-5 space-y-3">
            {history.feedback.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 text-sm text-zinc-500">No feedback has been captured yet.</div>
            ) : (
              history.feedback.map((item) => (
                <div key={item.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 text-sm text-zinc-200">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-zinc-100">Choice: {item.choice.toUpperCase()}</p>
                      <p className="text-xs text-zinc-500">{item.recorded_at}</p>
                    </div>
                    <div className="rounded-full border border-zinc-700 bg-zinc-950 px-3 py-1 text-xs uppercase tracking-[0.18em] text-zinc-400">Result {item.result_id}</div>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div>
                      <p className="text-xs text-zinc-500">Mix A</p>
                      <p className="text-sm text-zinc-300 break-all">{item.mix_a_path}</p>
                    </div>
                    <div>
                      <p className="text-xs text-zinc-500">Mix B</p>
                      <p className="text-sm text-zinc-300 break-all">{item.mix_b_path}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / Math.pow(1024, index)
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`
}
