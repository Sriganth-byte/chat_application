import { create } from 'zustand'
import api from '../api/axios'

const useChatStore = create((set) => ({
  rooms: [],
  activeRoom: null,
  messages: {},
  typingUsers: {},
  unreadCounts: {},
  searchResults: null,
  loading: false,
  error: null,

  incomingCall: null,
  callAnswer: null,
  iceCandidates: [],
  activeCall: null,
  callEndedAt: null,
  pendingAcceptedCall: null,

  fetchRooms: async () => {
    try {
      const response = await api.get('/chat/rooms/')
      const rooms = Array.isArray(response.data) ? response.data : (response.data?.results || [])
      const counts = {}
      rooms.forEach(r => { counts[r.id] = r.unread_count || 0 })
      set({ rooms, unreadCounts: counts, error: null })
    } catch (err) {
      console.error('Failed to fetch rooms:', err)
      set({ error: 'Failed to load rooms' })
    }
  },

  fetchRoomById: async (roomId) => {
    if (!roomId) return null
    try {
      const { data } = await api.get(`/chat/rooms/${roomId}/`)
      set(s => ({
        rooms: s.rooms.some(room => String(room.id) === String(data.id))
          ? s.rooms.map(room => String(room.id) === String(data.id) ? data : room)
          : [data, ...s.rooms],
        error: null,
      }))
      return data
    } catch (err) {
      console.error('Failed to fetch room:', err)
      set({ error: 'Failed to load room' })
      return null
    }
  },

  setActiveRoom: (room) => {
    if (!room) return
    set(s => ({
      activeRoom: room,
      unreadCounts: { ...s.unreadCounts, [room.id]: 0 },
    }))
  },

  fetchMessages: async (roomId) => {
    if (!roomId) return
    const key = String(roomId)
    set({ loading: true, error: null })

    try {
      const response = await api.get(`/chat/rooms/${roomId}/messages/`)
      let msgs = []
      if (response.data) {
        msgs = Array.isArray(response.data) ? response.data : (response.data?.results || [])
      }
      set(s => ({
        messages: { ...s.messages, [key]: [...msgs].reverse() },
        loading: false
      }))
    } catch (err) {
      console.error('Error fetching messages:', err)
      set({ loading: false, error: 'Failed to load messages' })
    }
  },

  addMessage: (roomId, msg) => {
    if (!roomId || !msg) return
    set(s => {
      const key = String(roomId)
      const prev = s.messages[key] || []
      if (prev.find(m => m.id === msg.id)) return {}
      // Use loose comparison to handle numeric vs string room IDs
      const rooms = s.rooms.map(r =>
        String(r.id) === String(roomId)
          ? { ...r, last_message: { content: msg.content, sender: msg.sender?.username, created_at: msg.created_at, message_type: msg.message_type } }
          : r
      )
      return {
        messages: { ...s.messages, [key]: [...prev, msg] },
        rooms,
      }
    })
  },

  updateMessage: (roomId, updated) => {
    if (!roomId || !updated) return
    set(s => ({
      messages: {
        ...s.messages,
        [String(roomId)]: (s.messages[String(roomId)] || []).map(m => m.id === updated.id ? updated : m),
      },
    }))
  },

  removeMessage: (roomId, messageId) => {
    if (!roomId || !messageId) return
    set(s => ({
      messages: {
        ...s.messages,
        [String(roomId)]: (s.messages[String(roomId)] || []).filter(m => m.id !== messageId),
      },
    }))
  },

  setTyping: (roomId, userId, username) => {
    if (!roomId || !userId) return
    set(s => ({
      typingUsers: {
        ...s.typingUsers,
        [String(roomId)]: { ...(s.typingUsers[String(roomId)] || {}), [userId]: username },
      },
    }))
  },

  clearTyping: (roomId, userId) => {
    if (!roomId || !userId) return
    set(s => {
      const room = { ...(s.typingUsers[String(roomId)] || {}) }
      delete room[userId]
      return { typingUsers: { ...s.typingUsers, [String(roomId)]: room } }
    })
  },

  incrementUnread: (roomId) => {
    if (!roomId) return
    set(s => ({
      unreadCounts: { ...s.unreadCounts, [roomId]: (s.unreadCounts[roomId] || 0) + 1 },
    }))
  },

  search: async (q, type = 'all') => {
    if (!q || !q.trim()) { set({ searchResults: null }); return }
    try {
      const { data } = await api.get(`/chat/search/?q=${encodeURIComponent(q)}&type=${type}`)
      set({ searchResults: data })
    } catch (err) {
      console.error('Search error:', err)
    }
  },

  clearSearch: () => set({ searchResults: null }),

  createRoom: async (payload) => {
    try {
      const { data } = await api.post('/chat/rooms/', payload)
      set(s => ({ rooms: [data, ...s.rooms] }))
      return data
    } catch (err) {
      console.error('Failed to create room:', err)
      throw err
    }
  },

  setIncomingCall: (call) => set({ incomingCall: call }),
  clearIncomingCall: () => set({ incomingCall: null }),
  setPendingAcceptedCall: (call) => set({ pendingAcceptedCall: call, incomingCall: null }),
  clearPendingAcceptedCall: () => set({ pendingAcceptedCall: null }),
  setCallAnswer: (answer) => set({ callAnswer: answer }),
  addIceCandidate: (candidate) => set(s => ({ iceCandidates: [...s.iceCandidates, candidate] })),
  clearIceCandidates: () => set({ iceCandidates: [] }),
  setActiveCall: (call) => set({ activeCall: call }),
  clearCall: () => set({ incomingCall: null, pendingAcceptedCall: null, callAnswer: null, iceCandidates: [], activeCall: null }),
  markCallEnded: () => set({
    incomingCall: null,
    pendingAcceptedCall: null,
    callAnswer: null,
    iceCandidates: [],
    activeCall: null,
    callEndedAt: Date.now(),
  }),
}))

export default useChatStore
