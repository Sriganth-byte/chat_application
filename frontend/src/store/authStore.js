import { create } from 'zustand'
import api from '../api/axios'

const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  access: localStorage.getItem('access') || null,
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const { data } = await api.post('/auth/login/', { email, password })
      localStorage.setItem('access', data.access)
      localStorage.setItem('refresh', data.refresh)
      const profile = await api.get('/auth/profile/')
      localStorage.setItem('user', JSON.stringify(profile.data))
      set({ user: profile.data, access: data.access, loading: false })
      return true
    } catch (err) {
      set({ error: err.response?.data?.detail || err.response?.data?.error || 'Invalid credentials', loading: false })
      return false
    }
  },

  register: async (payload) => {
    set({ loading: true, error: null })
    try {
      await api.post('/auth/register/', payload)
      set({ loading: false })
      return true
    } catch (err) {
      const errors = err.response?.data
      const msg = typeof errors === 'object'
        ? Object.values(errors).flat().join(' ')
        : 'Registration failed'
      set({ error: msg, loading: false })
      return false
    }
  },

  logout: async () => {
    try { await api.post('/auth/logout/') } catch {}
    localStorage.clear()
    set({ user: null, access: null })
  },

  updateUser: (data) => {
    const updated = { ...get().user, ...data }
    localStorage.setItem('user', JSON.stringify(updated))
    set({ user: updated })
  },

  clearError: () => set({ error: null }),
}))

export default useAuthStore
