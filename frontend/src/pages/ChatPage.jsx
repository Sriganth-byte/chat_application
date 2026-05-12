import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'
import Sidebar from '../components/Sidebar'
import MessagePanel from '../components/MessagePanel'
import EmptyState from '../components/EmptyState'
import s from './ChatPage.module.css'

export default function ChatPage() {
  const { user } = useAuthStore()
  const { fetchRooms, fetchRoomById, activeRoom, pendingAcceptedCall, rooms, setActiveRoom } = useChatStore()
  const navigate = useNavigate()
  const [initializing, setInitializing] = useState(true)
  const [showList, setShowList] = useState(true)
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 900px)').matches)

  useEffect(() => {
    if (!user) { navigate('/login'); return }

    const initChat = async () => {
      try {
        await fetchRooms()
      } catch (err) {
        console.error('[ChatPage] Failed to initialize chat:', err)
      } finally {
        setInitializing(false)
      }
    }

    initChat()
  }, [user, navigate, fetchRooms])

  useEffect(() => {
    if (typeof window === 'undefined') return

    const mediaQuery = window.matchMedia('(max-width: 900px)')
    const handleResize = (event) => setIsMobile(event.matches)

    mediaQuery.addEventListener?.('change', handleResize)
    mediaQuery.addListener?.(handleResize)

    return () => {
      mediaQuery.removeEventListener?.('change', handleResize)
      mediaQuery.removeListener?.(handleResize)
    }
  }, [])

  useEffect(() => {
    if (!pendingAcceptedCall?.roomId) return

    const pendingRoomId = String(pendingAcceptedCall.roomId)
    if (String(activeRoom?.id) === pendingRoomId && activeRoom?.members?.length) {
      return
    }

    const knownRoom = rooms.find(room => String(room.id) === pendingRoomId)
    if (knownRoom?.members?.length) {
      setActiveRoom(knownRoom)
      return
    }

    let cancelled = false

    async function resolvePendingCallRoom() {
      const fetchedRoom = await fetchRoomById(pendingAcceptedCall.roomId)
      if (!cancelled && fetchedRoom) {
        setActiveRoom(fetchedRoom)
      }
    }

    resolvePendingCallRoom()
    return () => { cancelled = true }
  }, [pendingAcceptedCall, activeRoom, rooms, fetchRoomById, setActiveRoom])

  const shouldOpenAcceptedCall = Boolean(
    isMobile &&
    activeRoom &&
    pendingAcceptedCall &&
    String(pendingAcceptedCall.roomId) === String(activeRoom.id)
  )
  const shouldBypassInitLoading = Boolean(pendingAcceptedCall)
  const shouldShowList = !isMobile || !activeRoom
    ? true
    : (shouldOpenAcceptedCall ? false : showList)

  if (initializing && !shouldBypassInitLoading) {
    return (
      <div className={s.shell} style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--c-text-3)' }}>Loading chat...</div>
      </div>
    )
  }

  return (
    <div className={s.shell}>
      {(!isMobile || shouldShowList) && (
        <Sidebar onRoomSelect={() => { if (isMobile) setShowList(false) }} />
      )}

      {(!isMobile || !shouldShowList || !activeRoom) && (
        <main className={s.main}>
          {activeRoom
            ? <MessagePanel isMobile={isMobile} onBack={() => setShowList(true)} />
            : <EmptyState />
          }
        </main>
      )}
    </div>
  )
}
