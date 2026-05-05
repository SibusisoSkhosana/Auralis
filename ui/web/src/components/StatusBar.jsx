import React from 'react'

export default function StatusBar({ stats, fileCount, busyLabel }) {
  const remaining = Math.max(0, 5 - Number(stats.valid || 0))

  return (
    <div className="flex h-9 shrink-0 items-center justify-between border-t border-zinc-800 bg-zinc-950 px-5 text-xs text-zinc-500">
      <div className="flex items-center gap-5">
        <span>{fileCount} source files</span>
        <span>{stats.valid} valid comparisons</span>
        <span>{stats.skipped} skipped</span>
      </div>
      <div className="flex items-center gap-2">
        {busyLabel ? (
          <>
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
            <span>{busyLabel}</span>
          </>
        ) : remaining === 0 ? (
          <span className="text-emerald-300">Training threshold reached</span>
        ) : (
          <span>{remaining} more to training threshold</span>
        )}
      </div>
    </div>
  )
}
