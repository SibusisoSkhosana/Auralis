import React, { useCallback, useContext, useState } from 'react'
import AudioPlayer from './AudioPlayer'
import { AudioContext } from '../context/AudioContext'

export default function MixComparison({ mix, isGenerating, canGenerate, onGenerateMixes }) {
  const audio = useContext(AudioContext)

  const handlePlayChange = useCallback(
    (url, shouldPlay) => {
      if (shouldPlay) {
        audio.play(url)
      } else {
        audio.pause()
      }
    },
    [audio]
  )

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
          {canGenerate && (
            <button
              className="mt-4 rounded-md border border-cyan-400/30 bg-cyan-400/10 px-6 py-2 text-sm font-medium text-cyan-100 hover:bg-cyan-400/15"
              onClick={onGenerateMixes}
            >
              Generate Mixes
            </button>
          )}
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
          Audio plays globally
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <AudioPlayer
          label="Mix A"
          audioUrl={mix.mixA_url}
          isPlaying={audio?.currentUrl === mix.mixA_url && audio?.isPlaying}
          onPlayChange={(shouldPlay) => handlePlayChange(mix.mixA_url, shouldPlay)}
          params={mix.paramsA}
          validation={mix.validationA}
        />
        <AudioPlayer
          label="Mix B"
          audioUrl={mix.mixB_url}
          isPlaying={audio?.currentUrl === mix.mixB_url && audio?.isPlaying}
          onPlayChange={(shouldPlay) => handlePlayChange(mix.mixB_url, shouldPlay)}
          params={mix.paramsB}
          validation={mix.validationB}
        />
      </div>
    </div>
  )
}
