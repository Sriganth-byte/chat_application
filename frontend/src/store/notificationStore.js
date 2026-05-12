import { create } from 'zustand'
import api from '../api/axios'

const useNotificationStore = create((set, get) => ({
  notifications: [],
  unreadCount: 0,
  loading: false,

  fetchNotifications: async () => {
    set({ loading: true })
    try {
      const { data } = await api.get('/notifications/')
      const unread = data.filter(n => !n.is_read).length
      set({ notifications: data, unreadCount: unread, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  markRead: async (id) => {
    try {
      await api.patch(`/notifications/${id}/`, { is_read: true })
      set(s => ({
        notifications: s.notifications.map(n => n.id === id ? { ...n, is_read: true } : n),
        unreadCount: Math.max(0, s.unreadCount - 1)
      }))
    } catch {}
  },

  markAllRead: async () => {
    try {
      await api.post('/notifications/mark-all-read/')
      set(s => ({
        notifications: s.notifications.map(n => ({ ...n, is_read: true })),
        unreadCount: 0
      }))
    } catch {}
  },

  addNotification: (notification) => {
    set(s => ({
      notifications: [notification, ...s.notifications].slice(0, 100),
      unreadCount: s.unreadCount + 1
    }))
  },
}))

export default useNotificationStore
