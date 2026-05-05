import React, { useEffect, useMemo, useRef, useState } from 'react'

const bars = [38, 56, 44, 72, 48, 64, 34, 82, 58, 46, 70, 40, 62, 76, 50, 68, 42, 54, 80, 36]

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0:00'
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

function formatValue(value) {
  if (typeof value === 'number') return Number.isInteger(value) ? value : value.toFixed(2)
  if (value === null || value === undefined) return '--'
  return String(value)
}

export default function AudioPlayer({ label, audioUrl, isPlaying, onPlayChange, params = {}, validation = {} }) {
  const audioRef = useRef(null)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [loadError, setLoadError] = useState(false)

  const progress = duration > 0 ? Math.min(currentTime / duration, 1) : 0
  const visibleParams = useMemo(() => Object.entries(params).slice(0, 6), [params])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const updateTime = () => setCurrentTime(audio.currentTime)
    const updateDuration = () => setDuration(Number.isFinite(audio.duration) ? audio.duration : 0)
    const handleEnded = () => onPlayChange(false)
    const handleError = () => setLoadError(true)
    const handleCanPlay = () => setLoadError(false)

    audio.addEventListener('timeupdate', updateTime)
    audio.addEventListener('loadedmetadata', updateDuration)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('error', handleError)
    audio.addEventListener('canplay', handleCanPlay)

    return () => {
      audio.removeEventListener('timeupdate', updateTime)
      audio.removeEventListener('loadedmetadata', updateDuration)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('error', handleError)
      audio.removeEventListener('canplay', handleCanPlay)
    }
  }, [onPlayChange])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.play().catch(() => onPlayChange(false))
    } else {
      audio.pause()
    }
  }, [isPlaying, onPlayChange])

  useEffect(() => {
    setCurrentTime(0)
    setDuration(0)
    setLoadError(false)
  }, [audioUrl])

  const seek = (event) => {
    if (!duration || !audioRef.current) return
    const rect = event.currentTarget.getBoundingClientRect()
    const nextProgress = Math.max(0, Math.min((event.clientX - rect.left) / rect.width, 1))
    audioRef.current.currentTime = nextProgress * duration
  }

  return (
    <article className="flex min-h-0 flex-col rounded-lg border border-zinc-800 bg-zinc-950">
      <div className="flex shrink-0 items-center justify-between border-b border-zinc-800 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-zinc-100">{label}</h3>
          <p className="mt-1 text-xs text-zinc-500">{validation?.is_good ? 'Validated for training' : 'Comparison render'}</p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-xs ${
          isPlaying
            ? 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100'
            : 'border-zinc-700 bg-zinc-900 text-zinc-500'
        }`}>
          {isPlaying ? 'Playing' : 'Idle'}
        </span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col p-4">
        <audio ref={audioRef} src={audioUrl} preload="metadata" />

        <div
          className="mb-5 grid h-28 items-end gap-1 rounded-md border border-zinc-800 bg-[#090b0d] px-3 py-3"
          style={{ gridTemplateColumns: `repeat(${bars.length}, minmax(0, 1fr))` }}
        >
          {bars.map((height, index) => {
            const filled = index / bars.length <= progress
            return (
              <span
                key={index}
                className={`rounded-sm transition-colors ${filled ? 'bg-cyan-300' : 'bg-zinc-800'}`}
                style={{ height: `${height}%` }}
              />
            )
          })}
        </div>

        <div className="flex items-center gap-3">
          <button
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-zinc-700 bg-zinc-900 text-sm font-semibold text-zinc-100 hover:border-cyan-400/50 hover:text-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => onPlayChange(!isPlaying)}
            disabled={!audioUrl || loadError}
            aria-label={isPlaying ? `Pause ${label}` : `Play ${label}`}
          >
            {isPlaying ? 'II' : 'Play'}
          </button>

          <div className="min-w-0 flex-1">
            <button
              type="button"
              className="block h-2 w-full rounded-full bg-zinc-800"
              onClick={seek}
              aria-label={`Seek ${label}`}
            >
              <span className="block h-full rounded-full bg-cyan-300" style={{ width: `${progress * 100}%` }} />
            </button>
            <div className="mt-2 flex justify-between text-xs tabular-nums text-zinc-500">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        </div>

        {loadError && (
          <p className="mt-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
            Audio failed to load. Check that the API server is running on port 5000.
          </p>
        )}

        <div className="mt-5 min-h-0 flex-1 overflow-y-auto rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Parameters</p>
            {validation?.peak_db !== undefined && (
              <p className="text-xs text-zinc-500">Peak {formatValue(validation.peak_db)} dB</p>
            )}
          </div>
          {visibleParams.length === 0 ? (
            <p className="text-xs text-zinc-500">No parameter metadata returned.</p>
          ) : (
            <div className="space-y-1.5 font-mono text-xs">
              {visibleParams.map(([key, value]) => (
                <div key={key} className="flex items-center justify-between gap-3">
                  <span className="truncate text-zinc-500">{key}</span>
                  <span className="shrink-0 text-zinc-200">{formatValue(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
