import React, { useEffect, useRef } from 'react'
import WaveSurfer from 'wavesurfer.js'

export default function WaveformTrack({
  label,
  audioUrl,
  offsetMs = 0,
  movable = false,
  onOffsetChange,
}) {
  const containerRef = useRef(null)
  const waveRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !audioUrl) return undefined

    const wave = WaveSurfer.create({
      container: containerRef.current,
      url: audioUrl,
      height: 58,
      barWidth: 2,
      barGap: 1,
      barRadius: 1,
      cursorWidth: 0,
      normalize: true,
      waveColor: movable ? '#3f3f46' : '#164e63',
      progressColor: movable ? '#a1a1aa' : '#67e8f9',
      interact: false,
    })

    waveRef.current = wave

    return () => {
      wave.destroy()
      waveRef.current = null
    }
  }, [audioUrl, movable])

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <div className="mb-3 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-zinc-100">{label}</p>
          <p className="text-xs text-zinc-500">{movable ? `${offsetMs} ms offset` : 'Reference beat'}</p>
        </div>
        {movable && (
          <input
            className="h-9 w-24 rounded-md border border-zinc-700 bg-zinc-900 px-2 text-right text-sm text-zinc-100 outline-none focus:border-cyan-400/60"
            type="number"
            min="-2000"
            max="2000"
            step="10"
            value={offsetMs}
            onChange={(event) => onOffsetChange(Number(event.target.value))}
          />
        )}
      </div>

      <div className="overflow-hidden rounded-md border border-zinc-800 bg-[#090b0d] px-3 py-2">
        <div
          className="transition-transform duration-150"
          style={{ transform: movable ? `translateX(${offsetMs / 20}px)` : 'translateX(0)' }}
        >
          <div ref={containerRef} />
        </div>
      </div>

      {movable && (
        <input
          className="mt-3 w-full accent-cyan-300"
          type="range"
          min="-2000"
          max="2000"
          step="10"
          value={offsetMs}
          onChange={(event) => onOffsetChange(Number(event.target.value))}
        />
      )}
    </div>
  )
}
