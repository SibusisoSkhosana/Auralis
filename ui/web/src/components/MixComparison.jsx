import React, { useCallback, useState } from 'react'
import AudioPlayer from './AudioPlayer'

export default function MixComparison({ mix, isGenerating }) {
  const [playingMix, setPlayingMix] = useState(null)

  const handlePlayChange = useCallback((mixId, shouldPlay) => {
    setPlayingMix(shouldPlay ? mixId : null)
  }, [])

  if (isGenerating) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950">
        <div className="w-full max-w-sm text-center">
          <div className="mx-auto mb-5 h-1.5 w-56 overflow-hidden rounded-full bg-zinc-800">
            <div className="h-full w-1/2 animate-meter rounded-full bg-cyan-300" />
          </div>
          <h2 className="text-base font-medium text-zinc-100">Rendering comparison mixes</h2>
          <p className="mt-2 text-sm text-zinc-500">Auralis is processing stems and exporting A/B audio.</p>
        </div>
      </div>
    )
  }

  if (!mix) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto mb-5 grid h-20 w-20 grid-cols-5 items-end gap-1">
            {[36, 64, 48, 78, 42].map((height, index) => (
              <span key={index} className="rounded-sm bg-zinc-700" style={{ height: `${height}%` }} />
            ))}
          </div>
          <h2 className="text-base font-medium text-zinc-100">Ready for a training pass</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            Add audio stems on the left, generate two mixes, then choose the version that feels better.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex shrink-0 items-center justify-between">
        <div>
          <h2 className="text-base font-medium text-zinc-100">A/B Comparison</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Generated {mix.generatedAt || 'just now'} from {mix.sourceFileCount || 0} source files.
          </p>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-500">
          One deck plays at a time
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <AudioPlayer
          label="Mix A"
          audioUrl={mix.mixA_url}
          isPlaying={playingMix === 'a'}
          onPlayChange={(shouldPlay) => handlePlayChange('a', shouldPlay)}
          params={mix.paramsA}
          validation={mix.validationA}
        />
        <AudioPlayer
          label="Mix B"
          audioUrl={mix.mixB_url}
          isPlaying={playingMix === 'b'}
          onPlayChange={(shouldPlay) => handlePlayChange('b', shouldPlay)}
          params={mix.paramsB}
          validation={mix.validationB}
        />
      </div>
    </div>
  )
}
