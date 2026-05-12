import { useRef } from 'react'
import { Phone, Video } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'
import { useNotificationSocket } from '../hooks/useNotificationSocket'
import Avatar from './ui/Avatar'
import s from './GlobalCallManager.module.css'

export default function GlobalCallManager() {
  const user = useAuthStore(state => state.user)
  const incomingCall = useChatStore(state => state.incomingCall)
  const rooms = useChatStore(state => state.rooms)
  const setActiveRoom = useChatStore(state => state.setActiveRoom)
  const fetchRoomById = useChatStore(state => state.fetchRoomById)
  const setPendingAcceptedCall = useChatStore(state => state.setPendingAcceptedCall)
  const clearIncomingCall = useChatStore(state => state.clearIncomingCall)
  const { send } = useNotificationSocket(Boolean(user))
  const navigate = useNavigate()
  const handlingRef = useRef(false)

  if (!user || !incomingCall) return null

  const accept = async () => {
    if (handlingRef.current) return
    handlingRef.current = true
    let room = rooms.find(item => String(item.id) === String(incomingCall.roomId))
    if (!room) {
      room = await fetchRoomById(incomingCall.roomId)
    }
    if (room) {
      setActiveRoom(room)
    }
    setPendingAcceptedCall(incomingCall)
    handlingRef.current = false
    navigate('/chat')
  }

  const decline = () => {
    if (handlingRef.current) return
    handlingRef.current = true
    send({
      type: 'call_decline',
      room_id: incomingCall.roomId,
      target_user: incomingCall.fromUser,
    })
    clearIncomingCall()
    handlingRef.current = false
  }

  const isVideo = incomingCall.callType === 'video'

  return (
    <div className={s.overlay} role="dialog" aria-modal="true" aria-label="Incoming call">
      <div className={s.card}>
        <div className={s.avatar}>
          <Avatar name={incomingCall.fromUsername || 'User'} size="xl" />
        </div>
        <div className={s.info}>
          <span className={s.name}>{incomingCall.fromUsername || 'Incoming call'}</span>
          <span className={s.type}>{isVideo ? 'Video call' : 'Voice call'} incoming...</span>
        </div>
        <div className={s.pulse} />
        <div className={s.actions}>
          <button className={[s.action, s.decline].join(' ')} type="button" onClick={decline} title="Decline call">
            <Phone size={24} />
          </button>
          <button className={[s.action, s.accept].join(' ')} type="button" onClick={accept} title="Accept call">
            {isVideo ? <Video size={24} /> : <Phone size={24} />}
          </button>
        </div>
      </div>
    </div>
  )
}
