import { useEffect, useRef, useCallback, useState } from 'react'
import useChatStore from '../store/chatStore'

const RECONNECT_DELAY_MS = 3000
const MAX_RECONNECT_ATTEMPTS = 5
const MAX_QUEUED_MESSAGES = 50

export function useWebSocket(roomId) {
  const ws = useRef(null)
  const reconnectTimer = useRef(null)
  const reconnectAttempts = useRef(0)
  const isMounted = useRef(true)
  const queuedMessages = useRef([])
  const [isOpen, setIsOpen] = useState(false)

  // Use getState() in callbacks to avoid stale closure over store methods
  const store = useChatStore

  // Stable send — silently drops if socket not open
  const flushQueue = useCallback(() => {
    if (ws.current?.readyState !== WebSocket.OPEN) return
    const pending = queuedMessages.current
    queuedMessages.current = []
    pending.forEach(payload => ws.current?.send(JSON.stringify(payload)))
  }, [])

  const send = useCallback((payload) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(payload))
      return true
    }
    queuedMessages.current = [...queuedMessages.current, payload].slice(-MAX_QUEUED_MESSAGES)
    return false
  }, [])

  useEffect(() => {
    if (!roomId) return
    isMounted.current = true
    reconnectAttempts.current = 0

    function connect() {
      if (!isMounted.current) return

      const token = localStorage.getItem('access')
      if (!token) return

      // Derive WS URL from the current page's host so it works on any IP/device.
      // Vite proxies /ws/* → ws://127.0.0.1:8000/ws/* (see vite.config.js).
      // Falls back to explicit VITE_WS_URL env var if set.
      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const wsBase = import.meta.env.VITE_WS_URL || `${wsProtocol}://${window.location.host}`
      const url = `${wsBase}/ws/chat/${roomId}/?token=${encodeURIComponent(token)}`
      const socket = new WebSocket(url)
      ws.current = socket

      socket.onopen = () => {
        reconnectAttempts.current = 0
        setIsOpen(true)
        flushQueue()
      }

      socket.onmessage = (e) => {
        let parsed
        try { parsed = JSON.parse(e.data) } catch { return }
        const { event, data } = parsed

        const {
          addMessage,
          updateMessage,
          removeMessage,
          setTyping,
          clearTyping,
        } = store.getState()

        switch (event) {
          case 'chat_history': {
            // Seed messages from WS history only if the REST load hasn't populated them yet
            const existing = store.getState().messages[roomId]
            if (!existing || existing.length === 0) {
              const historyMsgs = data?.messages || []
              // history arrives newest-first from the consumer; reverse for display
              store.setState(s => ({
                messages: {
                  ...s.messages,
                  [roomId]: [...historyMsgs].reverse(),
                },
              }))
            }
            break
          }

          case 'message_sent':
            // Delivery receipt for sender (message saved to DB)
            addMessage(roomId, data)
            break

          case 'message_received':
            // Broadcast to all room members (deduped by addMessage)
            addMessage(roomId, data)
            // Only mark seen for messages from others (not our own delivery receipt)
            if (data?.sender?.id !== store.getState().activeRoom?.members?.find?.(m => m?.user?.id)?.user?.id) {
              send({ type: 'message_seen', message_ids: [data?.id] })
            }
            break

          case 'message_edited':
            updateMessage(roomId, data)
            break

          case 'message_deleted':
            removeMessage(roomId, data?.message_id)
            break

          case 'message_consumed':
            updateMessage(roomId, data)
            break

          case 'message_seen':
            store.setState(s => ({
              messages: {
                ...s.messages,
                [roomId]: (s.messages[roomId] || []).map(m =>
                  data?.message_ids?.includes(m.id) ? { ...m, is_seen: true } : m
                ),
              },
            }))
            break

          case 'call_offer':
            // Keep room sockets as a fallback for users already in the chat,
            // while the notification socket handles ringing across the app.
            store.getState().setIncomingCall?.({
              roomId: data?.room_id || roomId,
              offer: data?.offer,
              callType: data?.call_type,
              fromUser: data?.from_user,
              fromUsername: data?.from_username,
            })
            break

          case 'call_answer':
            // Handle call answer
            store.setState({
              callAnswer: {
                roomId: data?.room_id,
                answer: data?.answer,
                fromUser: data?.from_user,
              }
            })
            break

          case 'call_ice':
            // Handle ICE candidate
            store.setState(s => ({
              iceCandidates: [...(s.iceCandidates || []), {
                roomId: data?.room_id,
                candidate: data?.candidate,
                fromUser: data?.from_user,
              }]
            }))
            break

          case 'call_end':
            store.getState().markCallEnded?.()
            break

          case 'call_declined':
            store.getState().markCallEnded?.()
            break

          case 'reaction_update':
            break

          case 'ping':
            send({ type: 'pong', timestamp: data?.timestamp })
            break

          case 'typing_start':
            setTyping(roomId, data?.user_id, data?.username)
            break

          case 'typing_stop':
            clearTyping(roomId, data?.user_id)
            break

          case 'error':
            console.warn('[WS] Server error:', data?.message)
            break

          default:
            break
        }
      }

      socket.onerror = () => {
        // onerror is always followed by onclose — handle reconnect there
      }

      socket.onclose = (e) => {
        setIsOpen(false)
        if (!isMounted.current) return
        // Don't reconnect on intentional close (code 1000) or auth failure (4001)
        if (e.code === 1000 || e.code === 4001) return

        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1
          const delay = RECONNECT_DELAY_MS * reconnectAttempts.current
          reconnectTimer.current = setTimeout(connect, delay)
        }
      }
    }

    connect()

    return () => {
      isMounted.current = false
      clearTimeout(reconnectTimer.current)
      if (ws.current) {
        ws.current.onclose = null  // prevent reconnect on intentional unmount
        ws.current.close(1000, 'Component unmounted')
        ws.current = null
      }
      queuedMessages.current = []
      setIsOpen(false)
    }
  }, [roomId, flushQueue, send, store])

  return { send, isOpen }
}
