import React, { createContext, useCallback, useRef, useState } from 'react'

export const AudioContext = createContext(null)

/**
 * Global Audio Context
 * 
 * Manages a single audio playback instance that persists across UI changes.
 * This prevents audio from stopping when switching views or modes.
 * 
 * Usage in components:
 * const audio = useContext(AudioContext)
 * audio.play(url) → start playback
 * audio.pause() → pause playback
 * audio.stop() → stop and reset
 */
export function AudioProvider({ children }) {
  const audioRef = useRef(new Audio())
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [currentUrl, setCurrentUrl] = useState(null)
  const [loadError, setLoadError] = useState(false)

  const audio = audioRef.current

  // Setup event listeners
  React.useEffect(() => {
    const handleTimeUpdate = () => setCurrentTime(audio.currentTime)
    const handleLoadedMetadata = () => setDuration(audio.duration || 0)
    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(0)
    }
    const handleError = () => setLoadError(true)
    const handleCanPlay = () => setLoadError(false)
    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('error', handleError)
    audio.addEventListener('canplay', handleCanPlay)
    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('error', handleError)
      audio.removeEventListener('canplay', handleCanPlay)
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
    }
  }, [audio])

  const play = useCallback(
    (url) => {
      if (url !== currentUrl) {
        audio.src = url
        setCurrentUrl(url)
        setCurrentTime(0)
        setDuration(0)
        setLoadError(false)
      }

      audio.play().catch(() => setIsPlaying(false))
      setIsPlaying(true)
    },
    [audio, currentUrl]
  )

  const pause = useCallback(() => {
    audio.pause()
    setIsPlaying(false)
  }, [audio])

  const stop = useCallback(() => {
    audio.pause()
    audio.currentTime = 0
    setCurrentTime(0)
    setIsPlaying(false)
    setCurrentUrl(null)
    audio.src = ''
  }, [audio])

  const seek = useCallback(
    (time) => {
      audio.currentTime = Math.max(0, Math.min(time, duration))
      setCurrentTime(audio.currentTime)
    },
    [audio, duration]
  )

  const togglePlayPause = useCallback(() => {
    if (isPlaying) {
      pause()
    } else if (currentUrl) {
      audio.play().catch(() => setIsPlaying(false))
      setIsPlaying(true)
    }
  }, [isPlaying, currentUrl, audio, pause])

  const value = {
    isPlaying,
    currentTime,
    duration,
    currentUrl,
    loadError,
    play,
    pause,
    stop,
    seek,
    togglePlayPause,
  }

  return <AudioContext.Provider value={value}>{children}</AudioContext.Provider>
}
