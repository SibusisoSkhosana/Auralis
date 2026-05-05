import React, { useRef, useState } from 'react'

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / Math.pow(1024, index)
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`
}

export default function Sidebar({
  files,
  fileSummary,
  onFileUpload,
  onFileRemove,
  onClearFiles,
  onGenerateMixes,
  canGenerate,
  loading,
  stats,
}) {
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  const ingestFiles = (fileList) => {
    onFileUpload(Array.from(fileList || []))
  }

  return (
    <aside className="flex w-[300px] shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium text-zinc-100">Sources</h2>
            <p className="text-xs text-zinc-500">Upload stems for comparison</p>
          </div>
          {files.length > 0 && (
            <button
              className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-400 hover:border-zinc-600 hover:text-zinc-100 disabled:opacity-50"
              onClick={onClearFiles}
              disabled={loading}
            >
              Clear
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setIsDragging(false)
            ingestFiles(event.dataTransfer.files)
          }}
          className={`flex h-28 w-full flex-col items-center justify-center rounded-md border border-dashed px-4 text-center transition ${
            isDragging
              ? 'border-cyan-400 bg-cyan-400/10 text-cyan-100'
              : 'border-zinc-700 bg-zinc-900/60 text-zinc-400 hover:border-zinc-600 hover:bg-zinc-900 hover:text-zinc-200'
          }`}
        >
          <span className="text-sm font-medium">Drop audio files</span>
          <span className="mt-1 text-xs text-zinc-500">or browse WAV, MP3, FLAC, OGG</span>
        </button>

        <input
          ref={inputRef}
          className="hidden"
          type="file"
          multiple
          accept="audio/*,.wav,.mp3,.flac,.ogg"
          onChange={(event) => {
            ingestFiles(event.target.files)
            event.target.value = ''
          }}
        />

        <button
          className="mt-4 flex h-10 w-full items-center justify-center rounded-md border border-cyan-400/30 bg-cyan-400/10 px-4 text-sm font-medium text-cyan-100 hover:border-cyan-300/50 hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:border-zinc-800 disabled:bg-zinc-900 disabled:text-zinc-500"
          onClick={onGenerateMixes}
          disabled={!canGenerate}
        >
          {loading ? 'Generating...' : 'Generate Mixes'}
        </button>
        <p className="mt-3 text-xs leading-5 text-zinc-500">
          Uploading replaces the active resources project and updates the mixer configuration.
          Name the beat file with "beat" or "instrumental"; otherwise the first file is used as the beat.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="mb-3 flex items-end justify-between">
          <div>
            <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Stem List</h3>
            <p className="mt-1 text-xs text-zinc-500">
              {fileSummary.count} selected, {formatFileSize(fileSummary.totalBytes)}
            </p>
          </div>
        </div>

        {files.length === 0 ? (
          <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-500">
            No stems selected.
          </div>
        ) : (
          <div className="space-y-2">
            {files.map((file, index) => (
              <div key={`${file.name}-${file.size}-${index}`} className="group rounded-md border border-zinc-800 bg-zinc-900/70 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-zinc-200">{file.name}</p>
                    <p className="mt-1 text-xs text-zinc-500">{formatFileSize(file.size)}</p>
                  </div>
                  <button
                    className="rounded border border-transparent px-2 py-0.5 text-xs text-zinc-500 hover:border-zinc-700 hover:text-zinc-200 disabled:opacity-50"
                    onClick={() => onFileRemove(index)}
                    disabled={loading}
                    aria-label={`Remove ${file.name}`}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-zinc-800 p-4">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Training</h3>
        <div className="grid grid-cols-3 gap-2">
          <Metric label="Total" value={stats.total} />
          <Metric label="Valid" value={stats.valid} />
          <Metric label="Skipped" value={stats.skipped} />
        </div>
      </div>
    </aside>
  )
}

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-900/70 p-3">
      <p className="text-lg font-semibold text-zinc-100">{value}</p>
      <p className="mt-1 text-[11px] text-zinc-500">{label}</p>
    </div>
  )
}
