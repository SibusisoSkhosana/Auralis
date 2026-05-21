import React, { useCallback, useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/Sidebar'
import UnifiedWorkspace from '../components/UnifiedWorkspace'
import { apiClient } from '../api/client'
import { useAuth } from '../context/AuthContext'

const initialStats = { total: 0, valid: 0, skipped: 0 }

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [files, setFiles] = useState([])
  const [currentMix, setCurrentMix] = useState(null)
  const [stats, setStats] = useState(initialStats)
  const [isGenerating, setIsGenerating] = useState(false)
  const [submittingChoice, setSubmittingChoice] = useState(null)
  const [project, setProject] = useState(null)
  const [currentSessionId, setCurrentSessionId] = useState(null)
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
    try {
      const data = await apiClient.getStats()
      setStats({
        total: Number(data.total || 0),
        valid: Number(data.valid || 0),
        skipped: Number(data.skipped || 0),
      })
    } catch (err) {
      console.error('Error loading stats', err)
    }
  }, [])

  const loadProject = useCallback(async () => {
    setIsProjectLoading(true)
    setError(null)
    try {
      const data = await apiClient.getProject()
      setProject(data)
      setCurrentSessionId(data.sessionId || null)
    } catch (err) {
      // Log error but don't show 422 on initial load (expected when no project configured)
      if (err.message && err.message.includes('422')) {
        console.warn('No active project yet:', err.message)
      } else {
        setError(err.message || 'Failed to load active project.')
      }
    } finally {
      setIsProjectLoading(false)
    }
  }, [])

  useEffect(() => {
    // Only load data after auth context has finished initialization
    if (!user) return
    loadStats()
    loadProject()
  }, [user, loadStats, loadProject])

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
      setCurrentSessionId(uploadedProject.sessionId || null)
      setNotice('Project uploaded. Generate mixes when ready.')
    } catch (err) {
      setError(err.message || 'Failed to upload active project.')
    } finally {
      setIsProjectLoading(false)
    }
  }, [])

  const handleFileUpload = useCallback(
    (incomingFiles) => {
      const audioFiles = incomingFiles.filter(
        (file) => file.type.startsWith('audio/') || /\.(wav|mp3|flac|ogg)$/i.test(file.name)
      )
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
    },
    [files, uploadActiveProject]
  )

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
      setCurrentSessionId(null)
      await loadProject()
      setNotice('Active project cleared. Upload the next project stems.')
    } catch (err) {
      setError(err.message || 'Failed to clear active project.')
    }
  }, [isBusy, loadProject])

  const handleGenerateMixes = useCallback(async () => {
    if (!canGenerate) return

    setIsGenerating(true)
    setCurrentMix(null)
    setError(null)
    setNotice(null)

    try {
      const payload = {}
      if (currentSessionId) {
        payload.sessionId = currentSessionId
      }
      const mixData = await apiClient.generateMixes(payload)
      setCurrentMix({
        ...mixData,
        resultId: mixData.resultId,
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
  }, [canGenerate, currentSessionId, files.length, loadProject])

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

  const handleSaveAlignment = useCallback(
    async (offsets) => {
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
    },
    [loadProject]
  )

  const handleSubmitFeedback = useCallback(
    async (choice) => {
      if (!canSubmit || !currentMix) return

      setSubmittingChoice(choice)
      setError(null)
      setNotice(null)

      try {
        await apiClient.submitFeedback({
          resultId: currentMix.resultId,
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
    },
    [canSubmit, currentMix, loadStats]
  )

  const handleDismissMessage = useCallback(() => {
    setError(null)
    setNotice(null)
  }, [])

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-5">
        <div>
          <h1 className="text-base font-semibold tracking-[0.16em] text-zinc-100">AURALIS</h1>
          <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">User dashboard</p>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <div className="rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1 text-zinc-300">
            {user?.email}
          </div>
          <button
            className="rounded border border-zinc-700 px-3 py-1 text-xs text-zinc-300 hover:border-zinc-600 hover:text-zinc-100"
            onClick={logout}
          >
            Sign out
          </button>
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
        >
          <div className="border-t border-zinc-800 p-4">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-4 text-sm text-zinc-300">
              <p className="font-semibold text-zinc-100">Consent</p>
              <p className="mt-2 text-xs text-zinc-500">
                {user?.consent_to_training
                  ? 'Your approved samples can be included in future model training.'
                  : 'You have not consented to training. Feedback will still be recorded for analytics.'}
              </p>
            </div>
          </div>
        </Sidebar>

        <UnifiedWorkspace
          files={files}
          currentMix={currentMix}
          isGenerating={isGenerating}
          project={project}
          projectLoading={isProjectLoading}
          syncing={isSyncing}
          saving={isSavingAlignment}
          stats={stats}
          error={error}
          notice={notice}
          onDismissMessage={handleDismissMessage}
          onRefreshProject={loadProject}
          onSyncAlignment={handleSyncAlignment}
          onSaveAlignment={handleSaveAlignment}
          onGenerateMixes={handleGenerateMixes}
          onFeedback={handleSubmitFeedback}
          canGenerate={canGenerate}
          canSubmit={canSubmit}
          submittingChoice={submittingChoice}
        />
      </div>
    </div>
  )
}
