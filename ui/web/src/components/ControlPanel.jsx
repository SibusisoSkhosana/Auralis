import React from 'react'

const choices = [
  { id: 'a', label: 'A Better', tone: 'cyan' },
  { id: 'b', label: 'B Better', tone: 'cyan' },
  { id: 'tie', label: 'Tie', tone: 'zinc' },
  { id: 'skip', label: 'Skip', tone: 'zinc' },
]

export default function ControlPanel({ onFeedback, disabled, submittingChoice }) {
  return (
    <footer className="shrink-0 border-t border-zinc-800 bg-zinc-950 px-5 py-4">
      <div className="mx-auto flex max-w-4xl flex-col gap-3">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm font-medium text-zinc-200">Which mix should train the next generation?</p>
          <p className="hidden text-xs text-zinc-500 sm:block">Submit once per comparison</p>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {choices.map((choice) => {
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
                disabled={disabled || Boolean(submittingChoice)}
                onClick={() => onFeedback(choice.id)}
              >
                {isSubmitting ? 'Submitting...' : choice.label}
              </button>
            )
          })}
        </div>
      </div>
    </footer>
  )
}
