import React, { useEffect, useMemo, useState } from 'react'
import WaveformTrack from './WaveformTrack'

export default function AlignmentView({
  project,
  loading,
  syncing,
  saving,
  onRefresh,
  onSync,
  onSave,
}) {
  const [offsets, setOffsets] = useState({})

  useEffect(() => {
    setOffsets(project?.offsets || {})
  }, [project])

  const hasProject = Boolean(project?.configured && project?.beat)
  const canSave = hasProject && !loading && !syncing && !saving

  const orderedVocals = useMemo(() => project?.vocals || [], [project])

  const updateOffset = (filename, value) => {
    const clamped = Math.max(-2000, Math.min(2000, Number(value) || 0))
    setOffsets((current) => ({ ...current, [filename]: clamped }))
  }

  const handleSync = async () => {
    const result = await onSync()
    if (result?.offsets) {
      setOffsets(result.offsets)
    }
  }

  const handleReset = () => {
    const reset = {}
    orderedVocals.forEach((vocal) => {
      reset[vocal.filename] = 0
    })
    setOffsets(reset)
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex shrink-0 items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-medium text-zinc-100">Alignment</h2>
          <p className="mt-1 text-sm text-zinc-500">Sync vocals to the reference beat before training comparisons.</p>
        </div>
        <button
          className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 hover:border-zinc-600 disabled:opacity-50"
          onClick={onRefresh}
          disabled={loading}
        >
          Refresh
        </button>
      </div>

      {!hasProject ? (
        <div className="flex flex-1 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 text-center">
          <div>
            <h3 className="text-sm font-medium text-zinc-100">No active project</h3>
            <p className="mt-2 text-sm text-zinc-500">Upload stems in Training, then return here to align them.</p>
          </div>
        </div>
      ) : (
        <>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
            <WaveformTrack
              label={project.beat.filename}
              audioUrl={project.beat.url}
              movable={false}
            />

            {orderedVocals.map((vocal) => (
              <WaveformTrack
                key={vocal.filename}
                label={vocal.filename}
                audioUrl={vocal.url}
                movable
                offsetMs={offsets[vocal.filename] ?? 0}
                onOffsetChange={(value) => updateOffset(vocal.filename, value)}
              />
            ))}
          </div>

          <div className="shrink-0 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <button
                className="h-10 rounded-md border border-cyan-400/30 bg-cyan-400/10 text-sm font-medium text-cyan-100 hover:bg-cyan-400/15 disabled:opacity-50"
                onClick={handleSync}
                disabled={!canSave}
              >
                {syncing ? 'Syncing...' : 'Sync'}
              </button>
              <button
                className="h-10 rounded-md border border-zinc-700 bg-zinc-900 text-sm font-medium text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                onClick={handleReset}
                disabled={!canSave}
              >
                Reset
              </button>
              <button
                className="h-10 rounded-md border border-emerald-400/30 bg-emerald-400/10 text-sm font-medium text-emerald-100 hover:bg-emerald-400/15 disabled:opacity-50"
                onClick={() => onSave(offsets)}
                disabled={!canSave}
              >
                {saving ? 'Saving...' : 'Save Alignment'}
              </button>
            </div>
            <p className="mt-3 text-xs leading-5 text-zinc-500">
              Positive offsets delay a vocal. Negative offsets move it earlier. Original audio files are not modified.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
