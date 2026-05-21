import React, { useContext, useState } from 'react'
import MixComparison from './MixComparison'
import AlignmentPanel from './AlignmentPanel'
import AlignmentView from './AlignmentView'
import { AudioContext } from '../context/AudioContext'

/**
 * UnifiedWorkspace
 * 
 * Single, continuous interface that supports both mix comparison training
 * and stem alignment without interrupting audio playback.
 * 
 * Layout:
 * - Top: Global audio player controls (shared across modes)
 * - Middle: Active workspace (Training or Alignment)
 * - Bottom: Control panel (changes based on active mode)
 */
export default function UnifiedWorkspace({
  files,
  currentMix,
  isGenerating,
  project,
  projectLoading,
  syncing,
  saving,
  stats,
  error,
  notice,
  onDismissMessage,
  onRefreshProject,
  onSyncAlignment,
  onSaveAlignment,
  onGenerateMixes,
  onFeedback,
  canGenerate,
  canSubmit,
  submittingChoice,
}) {
  const [mode, setMode] = useState('training') // 'training' | 'alignment'
  const audio = useContext(AudioContext)

  const hasProject = Boolean(project?.configured && project?.beat)

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#0b0d10]">
      {/* Messages */}
      {(error || notice) && (
        <div
          className={`mx-5 mt-4 rounded-md border px-4 py-3 text-sm ${
            error
              ? 'border-red-500/30 bg-red-500/10 text-red-200'
              : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-100'
          }`}
        >
          <div className="flex items-center justify-between gap-4">
            <span>{error || notice}</span>
            <button
              className="rounded px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              onClick={onDismissMessage}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Mode Tabs */}
      <div className="shrink-0 border-b border-zinc-800 bg-zinc-950/50 px-5 py-3">
        <div className="flex items-center justify-between">
          <nav className="flex items-center gap-2 text-sm">
            <button
              className={`rounded-md px-4 py-2 font-medium transition ${
                mode === 'training'
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'
              }`}
              onClick={() => setMode('training')}
            >
              🎯 Training
            </button>
            <button
              className={`rounded-md px-4 py-2 font-medium transition ${
                mode === 'alignment'
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'
              }`}
              onClick={() => {
                setMode('alignment')
                onRefreshProject()
              }}
            >
              🎚️ Alignment
            </button>
          </nav>

          {/* Global Playback Indicator */}
          <div className="flex items-center gap-3 text-xs">
            <div
              className={`h-2 w-2 rounded-full ${
                audio?.isPlaying ? 'animate-pulse bg-cyan-400' : 'bg-zinc-600'
              }`}
            />
            <span className="text-zinc-400">
              {audio?.isPlaying
                ? 'Audio playing'
                : audio?.currentUrl
                  ? 'Audio paused'
                  : 'No audio'}
            </span>
          </div>
        </div>
      </div>

      {/* Global Audio Player Controls */}
      {audio?.currentUrl && (
        <div className="shrink-0 border-b border-zinc-800 bg-zinc-950 px-5 py-3">
          <div className="flex items-center gap-4">
            <button
              className="flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700 bg-zinc-900 text-xs font-semibold text-zinc-100 hover:border-cyan-400/50 hover:text-cyan-100 disabled:opacity-50"
              onClick={audio.togglePlayPause}
              aria-label={audio.isPlaying ? 'Pause' : 'Play'}
            >
              {audio.isPlaying ? 'II' : '▶'}
            </button>

            <div className="flex min-w-0 flex-1 items-center gap-3">
              <span className="min-w-fit text-xs tabular-nums text-zinc-500">
                {formatTime(audio.currentTime)}
              </span>
              <button
                type="button"
                className="block h-1.5 w-full rounded-full bg-zinc-800"
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect()
                  const progress = Math.max(0, Math.min((e.clientX - rect.left) / rect.width, 1))
                  audio.seek(progress * audio.duration)
                }}
                aria-label="Seek"
              >
                <span
                  className="block h-full rounded-full bg-cyan-300 transition-all"
                  style={{ width: `${audio.duration > 0 ? (audio.currentTime / audio.duration) * 100 : 0}%` }}
                />
              </button>
              <span className="min-w-fit text-xs tabular-nums text-zinc-500">
                {formatTime(audio.duration)}
              </span>
            </div>

            <button
              className="text-xs text-zinc-500 hover:text-zinc-300"
              onClick={audio.stop}
              aria-label="Stop"
            >
              ⏹
            </button>
          </div>
        </div>
      )}

      {/* Main Workspace */}
      <section className="min-h-0 flex-1 overflow-hidden p-5">
        {mode === 'training' ? (
          <MixComparison
            mix={currentMix}
            isGenerating={isGenerating}
            canGenerate={canGenerate}
            onGenerateMixes={onGenerateMixes}
          />
        ) : (
          <>
            <AlignmentView
              project={project}
              loading={projectLoading}
              syncing={syncing}
              saving={saving}
              onRefresh={onRefreshProject}
              onSync={onSyncAlignment}
              onSave={onSaveAlignment}
            />
          </>
        )}
      </section>

      {/* Context-Aware Footer */}
      {mode === 'training' && currentMix && (
        <footer className="shrink-0 border-t border-zinc-800 bg-zinc-950 px-5 py-4">
          <div className="mx-auto flex max-w-4xl flex-col gap-3">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm font-medium text-zinc-200">Which mix should train the next generation?</p>
              <p className="hidden text-xs text-zinc-500 sm:block">Submit once per comparison</p>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                { id: 'a', label: 'A Better', tone: 'cyan' },
                { id: 'b', label: 'B Better', tone: 'cyan' },
                { id: 'tie', label: 'Tie', tone: 'zinc' },
                { id: 'skip', label: 'Skip', tone: 'zinc' },
              ].map((choice) => {
                const isSubmitting = submittingChoice === choice.id
                const isPrimary = choice.tone === 'cyan'
                return (
                  <button
                    key={choice.id}
                    className={`h-11 rounded-md border px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-45 ${
                      isPrimary
                        ? 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100 hover:border-cyan-300/50 hover:bg-cyan-400/15'
                        : 'border-zinc-700 bg-zinc-900 text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800'
                    }`}
                    disabled={!canSubmit || Boolean(submittingChoice)}
                    onClick={() => onFeedback(choice.id)}
                  >
                    {isSubmitting ? 'Submitting...' : choice.label}
                  </button>
                )
              })}
            </div>
          </div>
        </footer>
      )}

      {/* Training Stats Footer */}
      {mode === 'training' && (
        <div className="shrink-0 border-t border-zinc-800 bg-zinc-950 px-5 py-3">
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <div className="flex items-center gap-6">
              <span>
                <span className="font-medium text-zinc-100">{stats?.total || 0}</span> logged
              </span>
              <span>
                <span className="font-medium text-emerald-300">{stats?.valid || 0}</span> valid
              </span>
              <span>
                <span className="font-medium text-zinc-400">{stats?.skipped || 0}</span> skipped
              </span>
            </div>
            <span>{files?.length || 0} files loaded</span>
          </div>
        </div>
      )}
    </div>
  )
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0:00'
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}
