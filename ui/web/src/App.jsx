import React, { useCallback, useEffect, useMemo, useState } from 'react'
import Sidebar from './components/Sidebar'
import MixComparison from './components/MixComparison'
import ControlPanel from './components/ControlPanel'
import StatusBar from './components/StatusBar'
import AlignmentView from './components/AlignmentView'
import { apiClient } from './api/client'

const initialStats = { total: 0, valid: 0, skipped: 0 }

export default function App() {
  const [files, setFiles] = useState([])
  const [currentMix, setCurrentMix] = useState(null)
  const [stats, setStats] = useState(initialStats)
  const [isGenerating, setIsGenerating] = useState(false)
  const [submittingChoice, setSubmittingChoice] = useState(null)
  const [activeTab, setActiveTab] = useState('training')
  const [project, setProject] = useState(null)
  const [isProjectLoading, setIsProjectLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isSavingAlignment, setIsSavingAlignment] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)

  const isBusy = isGenerating || Boolean(submittingChoice) || isProjectLoading || isSyncing || isSavingAlignment
  const canGenerate = files.length > 0 && !isBusy
  const canSubmit = Boolean(currentMix) && !isBusy

  const fileSummary = useMemo(() => {
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0)
    return { count: files.length, totalBytes }
  }, [files])

  const loadStats = useCallback(async () => {
    const data = await apiClient.getStats()
    setStats({
      total: Number(data.total || 0),
      valid: Number(data.valid || 0),
      skipped: Number(data.skipped || 0),
    })
  }, [])

  const loadProject = useCallback(async () => {
    setIsProjectLoading(true)
    try {
      const data = await apiClient.getProject()
      setProject(data)
    } catch (err) {
      setError(err.message || 'Failed to load active project.')
    } finally {
      setIsProjectLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStats()
    loadProject()
  }, [loadStats, loadProject])

  const uploadActiveProject = useCallback(async (projectFiles) => {
    if (projectFiles.length < 2) return

    setIsProjectLoading(true)
    setError(null)
    setNotice(null)
    try {
      const formData = new FormData()
      projectFiles.forEach((file) => formData.append('files', file))
      const uploadedProject = await apiClient.uploadProject(formData)
      setProject(uploadedProject)
      setCurrentMix(null)
      setNotice('Project loaded. Open Alignment to sync vocals before generating mixes.')
    } catch (err) {
      setError(err.message || 'Failed to upload active project.')
    } finally {
      setIsProjectLoading(false)
    }
  }, [])

  const handleFileUpload = useCallback((incomingFiles) => {
    const audioFiles = incomingFiles.filter((file) => file.type.startsWith('audio/') || /\.(wav|mp3|flac|ogg)$/i.test(file.name))
    if (audioFiles.length === 0) {
      setError('Select WAV, MP3, FLAC, or OGG files.')
      return
    }

    const seen = new Set(files.map((file) => `${file.name}:${file.size}:${file.lastModified}`))
    const nextFiles = [...files]
    audioFiles.forEach((file) => {
      const key = `${file.name}:${file.size}:${file.lastModified}`
      if (!seen.has(key)) nextFiles.push(file)
    })

    setFiles(nextFiles)
    uploadActiveProject(nextFiles)
    setNotice(null)
    setError(null)
  }, [files, uploadActiveProject])

  const handleFileRemove = useCallback((index) => {
    setFiles((existing) => existing.filter((_, currentIndex) => currentIndex !== index))
  }, [])

  const handleClearFiles = useCallback(async () => {
    if (isBusy) return

    setError(null)
    setNotice(null)
    try {
      await apiClient.clearProject()
      setFiles([])
      setCurrentMix(null)
      await loadProject()
      setNotice('Active project cleared. Upload the next project stems.')
    } catch (err) {
      setError(err.message || 'Failed to clear active project.')
    }
  }, [isBusy])

  const handleGenerateMixes = useCallback(async () => {
    if (!canGenerate) return

    setIsGenerating(true)
    setCurrentMix(null)
    setError(null)
    setNotice(null)

    try {
      const mixData = await apiClient.generateMixes({})
      setCurrentMix({
        ...mixData,
        generatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sourceFileCount: files.length,
      })
      await loadProject()
      setNotice('Mixes generated. Compare A and B, then submit a preference.')
    } catch (err) {
      setError(err.message || 'Failed to generate mixes.')
    } finally {
      setIsGenerating(false)
    }
  }, [canGenerate, files, loadProject])

  const handleSyncAlignment = useCallback(async () => {
    setIsSyncing(true)
    setError(null)
    setNotice(null)
    try {
      const result = await apiClient.syncAlignment()
      setNotice(`Alignment synced (${result.layout || 'project'} layout). Review and save when ready.`)
      return result
    } catch (err) {
      setError(err.message || 'Failed to sync alignment.')
      return null
    } finally {
      setIsSyncing(false)
    }
  }, [])

  const handleSaveAlignment = useCallback(async (offsets) => {
    setIsSavingAlignment(true)
    setError(null)
    setNotice(null)
    try {
      await apiClient.saveAlignment(offsets)
      await loadProject()
      setNotice('Alignment saved. New mixes will use these offsets.')
    } catch (err) {
      setError(err.message || 'Failed to save alignment.')
    } finally {
      setIsSavingAlignment(false)
    }
  }, [loadProject])

  const handleSubmitFeedback = useCallback(async (choice) => {
    if (!canSubmit || !currentMix) return

    setSubmittingChoice(choice)
    setError(null)
    setNotice(null)

    try {
      await apiClient.submitFeedback({
        choice,
        paramsA: currentMix.paramsA,
        paramsB: currentMix.paramsB,
        metadata: {
          generatedAt: currentMix.generatedAt,
          sourceFileCount: currentMix.sourceFileCount,
          validationA: currentMix.validationA,
          validationB: currentMix.validationB,
        },
      })

      setCurrentMix(null)
      setNotice(choice === 'skip' ? 'Comparison skipped.' : 'Feedback recorded. Generate the next comparison when ready.')
      await loadStats()
    } catch (err) {
      setError(err.message || 'Failed to submit feedback.')
    } finally {
      setSubmittingChoice(null)
    }
  }, [canSubmit, currentMix, loadStats])

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-5">
        <div className="flex items-center gap-5">
          <div>
            <h1 className="text-base font-semibold tracking-[0.16em] text-zinc-100">AURALIS</h1>
            <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Training Console</p>
          </div>
          <nav className="hidden items-center gap-1 text-sm text-zinc-400 sm:flex">
            <button
              className={`rounded-md px-3 py-1.5 ${activeTab === 'training' ? 'bg-zinc-800 text-zinc-100' : 'hover:bg-zinc-900 hover:text-zinc-200'}`}
              onClick={() => setActiveTab('training')}
            >
              Training
            </button>
            <button
              className={`rounded-md px-3 py-1.5 ${activeTab === 'alignment' ? 'bg-zinc-800 text-zinc-100' : 'hover:bg-zinc-900 hover:text-zinc-200'}`}
              onClick={() => {
                setActiveTab('alignment')
                loadProject()
              }}
            >
              Alignment
            </button>
          </nav>
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className={`h-2 w-2 rounded-full ${isBusy ? 'bg-amber-400' : 'bg-emerald-400'}`} />
          <span>{isBusy ? 'Processing' : 'Ready'}</span>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <Sidebar
          files={files}
          fileSummary={fileSummary}
          onFileUpload={handleFileUpload}
          onFileRemove={handleFileRemove}
          onClearFiles={handleClearFiles}
          onGenerateMixes={handleGenerateMixes}
          canGenerate={canGenerate}
          loading={isGenerating || isProjectLoading}
          stats={stats}
        />

        <main className="flex min-w-0 flex-1 flex-col bg-[#0b0d10]">
          {(error || notice) && (
            <div className={`mx-5 mt-4 rounded-md border px-4 py-3 text-sm ${
              error
                ? 'border-red-500/30 bg-red-500/10 text-red-200'
                : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-100'
            }`}>
              <div className="flex items-center justify-between gap-4">
                <span>{error || notice}</span>
                <button
                  className="rounded px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                  onClick={() => {
                    setError(null)
                    setNotice(null)
                  }}
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          <section className="min-h-0 flex-1 overflow-hidden p-5">
            {activeTab === 'alignment' ? (
              <AlignmentView
                project={project}
                loading={isProjectLoading}
                syncing={isSyncing}
                saving={isSavingAlignment}
                onRefresh={loadProject}
                onSync={handleSyncAlignment}
                onSave={handleSaveAlignment}
              />
            ) : (
              <MixComparison mix={currentMix} isGenerating={isGenerating} />
            )}
          </section>

          {activeTab === 'training' && (
            <ControlPanel
              disabled={!canSubmit}
              submittingChoice={submittingChoice}
              onFeedback={handleSubmitFeedback}
            />
          )}

          <StatusBar
            stats={stats}
            fileCount={files.length}
            busyLabel={isGenerating ? 'Generating mixes' : submittingChoice ? 'Submitting feedback' : null}
          />
        </main>
      </div>
    </div>
  )
}
