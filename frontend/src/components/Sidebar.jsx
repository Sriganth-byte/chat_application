import { useState, useEffect } from 'react'
import { Search, Plus, Hash, MessageCircle, Users, Settings, LogOut, X, Zap } from 'lucide-react'
import { toast } from 'react-hot-toast'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'
import Avatar from './ui/Avatar'
import NewRoomModal from './chat/NewRoomModal'
import s from './Sidebar.module.css'
import { formatDistanceToNow } from 'date-fns'

export default function Sidebar({ onRoomSelect }) {
  const { user, logout } = useAuthStore()
  const { rooms, activeRoom, setActiveRoom, fetchMessages, searchResults, search, clearSearch } = useChatStore()
  const [query, setQuery] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    if (query) {
      const t = setTimeout(() => search(query), 300)
      return () => clearTimeout(t)
    }
  }, [query])

  const handleRoom = async (room) => {
    setActiveRoom(room)
    try {
      await fetchMessages(room.id)
    } catch (err) {
      console.error('Failed to fetch messages:', err)
      toast.error('Failed to load messages')
    }
    clearSearch()
    setQuery('')
    onRoomSelect?.()
  }

  const filtered = rooms.filter(r => {
    if (filter === 'dm')    return r.type === 'dm'
    if (filter === 'group') return r.type === 'group'
    return true
  })

  const displayRooms = query && searchResults?.rooms ? searchResults.rooms : filtered

  return (
    <aside className={s.sidebar}>

      {/* ── Header ── */}
      <div className={s.header}>
        <div className={s.wordmark}>
          <Zap size={16} strokeWidth={2.5} />
          <span>MindConnect</span>
        </div>
        <button className={s.newBtn} onClick={() => setShowModal(true)} title="New conversation">
          <Plus size={16} strokeWidth={2.5} />
        </button>
      </div>

      {/* ── Search ── */}
      <div className={s.searchWrap}>
        <Search size={14} className={s.searchIcon} />
        <input
          className={s.searchInput}
          placeholder="Search conversations…"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        {query && (
          <button className={s.clearBtn} onClick={() => { setQuery(''); clearSearch() }}>
            <X size={12} />
          </button>
        )}
      </div>

      {/* ── Filter tabs ── */}
      <div className={s.tabs}>
        {[['all','All'],['dm','Direct'],['group','Groups']].map(([v,l]) => (
          <button key={v} className={[s.tab, filter===v ? s.tabActive : ''].join(' ')}
            onClick={() => setFilter(v)}>{l}</button>
        ))}
      </div>

      {/* ── Room list ── */}
      <div className={s.list}>
        {displayRooms.length === 0 && (
          <div className={s.empty}>
            <MessageCircle size={28} strokeWidth={1.5} />
            <span>No conversations yet</span>
          </div>
        )}
        {displayRooms.map(room => (
          <RoomRow
            key={room.id}
            room={room}
            active={activeRoom?.id === room.id}
            onClick={() => handleRoom(room)}
            currentUser={user}
          />
        ))}

        {/* Search: users */}
        {query && searchResults?.users?.length > 0 && (
          <>
            <div className={s.sectionLabel}>People</div>
            {searchResults.users.map(u => (
              <div key={u.id} className={s.userRow}>
                <Avatar name={u.username} src={u.avatar_url} size="sm" online={u.is_online} />
                <div className={s.userInfo}>
                  <span className={s.userName}>{u.username}</span>
                  <span className={s.userEmail}>{u.email}</span>
                </div>
              </div>
            ))}
          </>
        )}
      </div>

      {/* ── Profile footer ── */}
      <div className={s.footer}>
        <Avatar name={user?.username || ''} src={user?.avatar_url} size="sm" online />
        <div className={s.footerInfo}>
          <span className={s.footerName}>{user?.username}</span>
          <span className={s.footerStatus}>
            <span className={s.onlineDot} />
            Online
          </span>
        </div>
        <div className={s.footerActions}>
          <button className={s.iconBtn} title="Settings"><Settings size={15} /></button>
          <button className={s.iconBtn} title="Sign out" onClick={logout}><LogOut size={15} /></button>
        </div>
      </div>

      {showModal && <NewRoomModal onClose={() => setShowModal(false)} />}
    </aside>
  )
}

function RoomRow({ room, active, onClick, currentUser }) {
  const { unreadCounts } = useChatStore()
  const unread = unreadCounts[room.id] || 0
  const isGroup = room.type === 'group'

  const otherMember = !isGroup
    ? room.members?.find(m => m.user.id !== currentUser?.id)?.user
    : null

  const displayName = isGroup
    ? room.name
    : otherMember?.username || 'Direct Message'

  const avatarName = isGroup ? room.name : (otherMember?.username || '')
  const isOnline = !isGroup && otherMember?.is_online

  const lastMsg = room.last_message
  const lastText = lastMsg
    ? lastMsg.message_type !== 'text'
      ? `📎 ${lastMsg.message_type}`
      : lastMsg.content
    : 'No messages yet'

  const lastTime = lastMsg?.created_at
    ? formatDistanceToNow(new Date(lastMsg.created_at), { addSuffix: false })
    : ''

  return (
    <button className={[s.roomRow, active ? s.roomActive : ''].join(' ')} onClick={onClick}>
      <div className={s.roomAvatar}>
        {isGroup
          ? <div className={s.groupIcon}><Hash size={16} /></div>
          : <Avatar name={avatarName} size="md" online={isOnline} />
        }
      </div>
      <div className={s.roomInfo}>
        <div className={s.roomTop}>
          <span className={s.roomName}>{displayName}</span>
          {lastTime && <span className={s.roomTime}>{lastTime}</span>}
        </div>
        <div className={s.roomBottom}>
          <span className={[s.roomLast, unread > 0 ? s.roomLastUnread : ''].join(' ')}>
            {lastText.length > 36 ? lastText.slice(0, 36) + '…' : lastText}
          </span>
          {unread > 0 && (
            <span className={s.badge}>{unread > 99 ? '99+' : unread}</span>
          )}
        </div>
      </div>
    </button>
  )
}
