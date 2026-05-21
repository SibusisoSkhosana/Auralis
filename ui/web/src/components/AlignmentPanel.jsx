import React from 'react'

/**
 * AlignmentPanel
 * 
 * Sidebar panel for alignment controls in unified workspace.
 * Complements the main AlignmentView by providing quick stats and actions.
 */
export default function AlignmentPanel({
  project,
  isLoading,
  onRefresh,
  onOpenAlignment,
}) {
  const hasProject = Boolean(project?.configured && project?.beat)
  const vocalCount = project?.vocals?.length || 0

  return (
    <div className="space-y-3 border-t border-zinc-800 p-4">
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">Alignment</h3>
        <p className="mt-1 text-xs text-zinc-500">
          {hasProject
            ? `${vocalCount} vocal stem${vocalCount !== 1 ? 's' : ''} loaded`
            : 'No stems loaded'}
        </p>
      </div>

      {hasProject && (
        <button
          className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-medium text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800 disabled:opacity-50"
          onClick={onOpenAlignment}
          disabled={isLoading}
        >
          {isLoading ? 'Loading...' : 'Sync Vocals'}
        </button>
      )}

      <button
        className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-medium text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800 disabled:opacity-50"
        onClick={onRefresh}
        disabled={isLoading}
      >
        {isLoading ? 'Refreshing...' : 'Refresh'}
      </button>
    </div>
  )
}
