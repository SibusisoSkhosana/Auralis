import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? '/api' : 'http://localhost:5000/api')
const apiUrl = API_BASE_URL.startsWith('/') ? `${window.location.origin}${API_BASE_URL}` : API_BASE_URL
const apiOrigin = new URL(apiUrl, window.location.origin).origin
const AUTH_STORAGE = 'auralis_auth_token'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

export function setAuthToken(token) {
  if (token) {
    client.defaults.headers.common.Authorization = `Bearer ${token}`
    localStorage.setItem(AUTH_STORAGE, token)
  } else {
    delete client.defaults.headers.common.Authorization
    localStorage.removeItem(AUTH_STORAGE)
  }
}

const storedToken = localStorage.getItem(AUTH_STORAGE)
if (storedToken) {
  setAuthToken(storedToken)
} else {
  const savedAuth = localStorage.getItem('auralis_auth')
  if (savedAuth) {
    try {
      const parsed = JSON.parse(savedAuth)
      if (parsed?.token) {
        setAuthToken(parsed.token)
      }
    } catch {
      // ignore malformed storage
    }
  }
}

function messageFromError(error, fallback) {
  return error.response?.data?.error || error.message || fallback
}

function resolveAudioUrl(url) {
  if (!url) return ''
  return new URL(url, apiOrigin).href
}

function resolveProjectAudio(project) {
  if (!project?.configured) return project
  return {
    ...project,
    beat: project.beat ? { ...project.beat, url: resolveAudioUrl(project.beat.url) } : null,
    vocals: (project.vocals || []).map((vocal) => ({
      ...vocal,
      url: resolveAudioUrl(vocal.url),
    })),
  }
}

export const apiClient = {
  async register(payload) {
    try {
      const response = await client.post('/auth/register', payload)
      return response.data
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to register.'))
    }
  },

  async login(payload) {
    try {
      const response = await client.post('/auth/login', payload)
      return response.data
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to sign in.'))
    }
  },

  async generateMixes(payload) {
    try {
      const response = await client.post('/generate-mixes', payload)
      return {
        ...response.data,
        mixA_url: resolveAudioUrl(response.data.mixA_url),
        mixB_url: resolveAudioUrl(response.data.mixB_url),
      }
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to generate mixes.'))
    }
  },

  async submitFeedback(feedbackData) {
    try {
      const response = await client.post('/feedback', feedbackData)
      return response.data
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to submit feedback.'))
    }
  },

  async clearProject() {
    try {
      const response = await client.post('/project/clear')
      return response.data
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to clear active project.'))
    }
  },

  async uploadProject(formData) {
    try {
      const response = await client.post('/upload', formData)
      return resolveProjectAudio(response.data)
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to upload active project.'))
    }
  },

  async getProject() {
    try {
      const response = await client.get('/project')
      return resolveProjectAudio(response.data)
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to load active project.'))
    }
  },

  async syncAlignment() {
    try {
      const response = await client.post('/alignment/sync')
      return response.data
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to sync alignment.'))
    }
  },

  async saveAlignment(offsets) {
    try {
      const response = await client.post('/alignment', { offsets })
      return response.data
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to save alignment.'))
    }
  },

  async getHistory() {
    try {
      const response = await client.get('/history')
      return response.data
    } catch (error) {
      throw new Error(messageFromError(error, 'Failed to load history.'))
    }
  },

  async getStats() {
    try {
      const response = await client.get('/stats')
      return response.data
    } catch {
      return { total: 0, valid: 0, skipped: 0 }
    }
  },

  async healthCheck() {
    try {
      const response = await client.get('/health')
      return response.status === 200
    } catch {
      return false
    }
  },
}
