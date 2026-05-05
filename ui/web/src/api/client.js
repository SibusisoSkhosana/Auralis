import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'
const apiOrigin = new URL(API_BASE_URL).origin

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

function messageFromError(error, fallback) {
  return error.response?.data?.error || error.message || fallback
}

function resolveAudioUrl(url) {
  if (!url) return ''
  return new URL(url, apiOrigin).href
}

export const apiClient = {
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
      const response = await client.post('/submit-feedback', feedbackData)
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
