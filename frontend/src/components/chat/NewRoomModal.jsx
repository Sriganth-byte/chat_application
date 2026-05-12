import { useState, useEffect } from 'react'
import { X, Search, Hash, MessageCircle, Check } from 'lucide-react'
import api from '../../api/axios'
import useChatStore from '../../store/chatStore'
import Avatar from '../ui/Avatar'
import s from './NewRoomModal.module.css'

export default function NewRoomModal({ onClose }) {
  const { createRoom, setActiveRoom, fetchMessages } = useChatStore()
  const [tab, setTab] = useState('dm')       // dm | group
  const [query, setQuery] = useState('')
  const [users, setUsers] = useState([])
  const [selected, setSelected] = useState([])
  const [groupName, setGroupName] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!query.trim()) { setUsers([]); return }
      try {
        const { data } = await api.get(`/auth/users/?q=${encodeURIComponent(query)}`)
        setUsers(data?.results || data || [])
      } catch { setUsers([]) }
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  const toggle = (u) => {
    if (tab === 'dm') { setSelected([u]); return }
    setSelected(s => s.find(x => x.id === u.id) ? s.filter(x => x.id !== u.id) : [...s, u])
  }

  const submit = async () => {
    if (selected.length === 0) return
    if (tab === 'group' && !groupName.trim()) return
    setLoading(true)
    try {
      const { rooms } = useChatStore.getState()

      // For DM: reuse existing room with this user instead of creating a duplicate
      if (tab === 'dm' && selected.length === 1) {
        const targetId = selected[0].id
        const existing = rooms.find(r =>
          r.type === 'dm' &&
          r.members?.some(m => m.user.id === targetId)
        )
        if (existing) {
          setActiveRoom(existing)
          await fetchMessages(existing.id)
          onClose()
          setLoading(false)
          return
        }
      }

      const room = await createRoom({
        name: tab === 'group' ? groupName.trim() : '',
        type: tab,
        ...(tab === 'dm'
          ? { user_id: selected[0].id }
          : { members: selected.map(u => u.id) }),
      })
      setActiveRoom(room)
      await fetchMessages(room.id)
      onClose()
    } catch (e) {
      console.error('Create room failed:', e?.response?.data || e)
    }
    setLoading(false)
  }

  return (
    <div className={s.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={s.modal}>

        <div className={s.modalHeader}>
          <h3 className={s.modalTitle}>New conversation</h3>
          <button className={s.closeBtn} onClick={onClose}><X size={16} /></button>
        </div>

        {/* Tabs */}
        <div className={s.tabs}>
          <button className={[s.tab, tab==='dm' ? s.tabActive : ''].join(' ')} onClick={() => { setTab('dm'); setSelected([]) }}>
            <MessageCircle size={14} />Direct message
          </button>
          <button className={[s.tab, tab==='group' ? s.tabActive : ''].join(' ')} onClick={() => { setTab('group'); setSelected([]) }}>
            <Hash size={14} />Group chat
          </button>
        </div>

        {tab === 'group' && (
          <div className={s.groupNameWrap}>
            <input className={s.groupNameInput} placeholder="Group name…"
              value={groupName} onChange={e => setGroupName(e.target.value)} autoFocus />
          </div>
        )}

        {/* Selected chips */}
        {selected.length > 0 && (
          <div className={s.chips}>
            {selected.map(u => (
              <div key={u.id} className={s.chip}>
                <Avatar name={u.username} size="xs" />
                <span>{u.username}</span>
                <button onClick={() => toggle(u)}><X size={10} /></button>
              </div>
            ))}
          </div>
        )}

        {/* Search */}
        <div className={s.searchWrap}>
          <Search size={14} className={s.searchIcon} />
          <input className={s.searchInput} placeholder="Search people…"
            value={query} onChange={e => setQuery(e.target.value)} autoFocus={tab === 'dm'} />
        </div>

        {/* Results */}
        <div className={s.results}>
          {users.length === 0 && query && (
            <div className={s.noResults}>No users found for "{query}"</div>
          )}
          {users.map(u => {
            const isSelected = selected.find(x => x.id === u.id)
            return (
              <button key={u.id} className={[s.userRow, isSelected ? s.userSelected : ''].join(' ')} onClick={() => toggle(u)}>
                <Avatar name={u.username} src={u.avatar_url} size="sm" online={u.is_online} />
                <div className={s.userInfo}>
                  <span className={s.userName}>{u.username}</span>
                  <span className={s.userEmail}>{u.email}</span>
                </div>
                {isSelected && <Check size={14} className={s.checkIcon} />}
              </button>
            )
          })}
        </div>

        <div className={s.footer}>
          <button className={s.cancelBtn} onClick={onClose}>Cancel</button>
          <button
            className={s.createBtn}
            onClick={submit}
            disabled={loading || selected.length === 0 || (tab === 'group' && !groupName.trim())}
          >
            {loading ? 'Creating…' : tab === 'dm' ? 'Open chat' : 'Create group'}
          </button>
        </div>

      </div>
    </div>
  )
}
