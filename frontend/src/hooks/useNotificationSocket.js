import { useEffect, useRef } from 'react'
import useChatStore from '../store/chatStore'
import useNotificationStore from '../store/notificationStore'

const RECONNECT_DELAY_MS = 3000
const MAX_RECONNECT_ATTEMPTS = 5
const MAX_QUEUED_MESSAGES = 20

export function useNotificationSocket(enabled = true) {
  const ws = useRef(null)
  const reconnectTimer = useRef(null)
  const reconnectAttempts = useRef(0)
  const isMounted = useRef(true)
  const queuedMessages = useRef([])

  const flushQueue = () => {
    if (ws.current?.readyState !== WebSocket.OPEN) return
    const pending = queuedMessages.current
    queuedMessages.current = []
    pending.forEach(payload => ws.current?.send(JSON.stringify(payload)))
  }

  useEffect(() => {
    if (!enabled) return
    isMounted.current = true
    reconnectAttempts.current = 0

    function connect() {
      if (!isMounted.current) return

      const token = localStorage.getItem('access')
      if (!token) return

      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const wsBase = import.meta.env.VITE_WS_URL || `${wsProtocol}://${window.location.host}`
      const socket = new WebSocket(`${wsBase}/ws/notifications/?token=${encodeURIComponent(token)}`)
      ws.current = socket

      socket.onopen = () => {
        reconnectAttempts.current = 0
        flushQueue()
      }

      socket.onmessage = (event) => {
        let parsed
        try { parsed = JSON.parse(event.data) } catch { return }

        const { event: eventName, data } = parsed
        const chatStore = useChatStore.getState()

        switch (eventName) {
          case 'notification':
            useNotificationStore.getState().addNotification(data)
            if (data?.data?.event === 'call_offer') {
              chatStore.setIncomingCall?.({
                roomId: data.data.room_id,
                offer: data.data.offer,
                callType: data.data.call_type,
                fromUser: data.data.from_user,
                fromUsername: data.data.from_username,
              })
            } else if (data?.data?.event === 'call_end' || data?.data?.event === 'call_declined') {
              chatStore.markCallEnded?.()
            }
            break

          case 'call_offer':
            chatStore.setIncomingCall?.({
              roomId: data?.room_id,
              offer: data?.offer,
              callType: data?.call_type,
              fromUser: data?.from_user,
              fromUsername: data?.from_username,
            })
            break

          case 'call_end':
          case 'call_declined':
            chatStore.markCallEnded?.()
            break

          default:
            break
        }
      }

      socket.onclose = (event) => {
        if (!isMounted.current) return
        if (event.code === 1000 || event.code === 4001) return

        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS * reconnectAttempts.current)
        }
      }
    }

    connect()

    return () => {
      isMounted.current = false
      clearTimeout(reconnectTimer.current)
      if (ws.current) {
        ws.current.onclose = null
        ws.current.close(1000, 'Component unmounted')
        ws.current = null
      }
      queuedMessages.current = []
    }
  }, [enabled])

  return {
    send: (payload) => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify(payload))
        return true
      }
      queuedMessages.current = [...queuedMessages.current, payload].slice(-MAX_QUEUED_MESSAGES)
      return false
    },
  }
}
