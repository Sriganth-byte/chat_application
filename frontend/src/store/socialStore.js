import { create } from 'zustand'
import api from '../api/axios'

const useSocialStore = create((set, get) => ({
  friends: [],
  friendRequests: [],
  suggestions: [],
  loading: false,

  fetchFriends: async () => {
    try {
      const { data } = await api.get('/social/friends/')
      set({ friends: data })
    } catch {}
  },

  fetchFriendRequests: async () => {
    try {
      const { data } = await api.get('/social/friend-requests/?direction=received')
      set({ friendRequests: data })
    } catch {}
  },

  fetchSuggestions: async () => {
    try {
      const { data } = await api.get('/social/suggestions/')
      set({ suggestions: data })
    } catch {}
  },

  sendFriendRequest: async (userId) => {
    const { data } = await api.post('/social/friend-request/', { user_id: userId })
    return data
  },

  respondToRequest: async (requestId, action) => {
    await api.patch(`/social/friend-request/${requestId}/`, { action })
    get().fetchFriendRequests()
    if (action === 'accept') get().fetchFriends()
  },

  toggleFollow: async (userId) => {
    const { data } = await api.post(`/social/follow/${userId}/`)
    return data
  },

  unfriend: async (userId) => {
    await api.delete(`/social/friends/${userId}/`)
    set(s => ({ friends: s.friends.filter(f => f.id !== userId) }))
  },
}))

export default useSocialStore
