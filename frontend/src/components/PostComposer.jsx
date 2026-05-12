import { useState, useEffect, useRef } from 'react'
import { Image, Video, Globe, Users, Lock, X, Loader2, BarChart2 } from 'lucide-react'
import api from '../api/axios'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'

const VISIBILITY_ICONS = { public: Globe, friends: Users, private: Lock }
const VISIBILITY_LABELS = { public: 'Public', friends: 'Friends', private: 'Only Me' }

// ─── @Mention Autocomplete ────────────────────────────────────────────────────
function MentionAutocomplete({ query, onSelect, position }) {
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(0)

  useEffect(() => {
    if (!query) { setResults([]); return }
    api.get(`/auth/users/?q=${encodeURIComponent(query)}`).then(r => {
      setResults((r.data || []).slice(0, 6))
      setSelected(0)
    }).catch(() => setResults([]))
  }, [query])

  if (!results.length) return null

  return (
    <div className="mention-dropdown" style={{ position: 'absolute', bottom: '100%', left: position, marginBottom: 4 }}>
      {results.map((u, i) => (
        <div key={u.id} className={`mention-item ${i === selected ? 'selected' : ''}`} onMouseDown={() => onSelect(u.username)}>
          <div className="avatar avatar-sm">
            {u.avatar_url ? <img src={u.avatar_url} alt="" /> : <span>{u.username?.[0]?.toUpperCase()}</span>}
          </div>
          <span style={{ fontWeight: 500, fontSize: '0.86rem' }}>{u.username}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Poll Builder ─────────────────────────────────────────────────────────────
function PollBuilder({ poll, onChange }) {
  const [options, setOptions] = useState(['', ''])

  useEffect(() => {
    onChange({ question: poll.question, options, closesIn: poll.closesIn })
  }, [options])

  const updateOption = (i, val) => setOptions(prev => prev.map((o, idx) => idx === i ? val : o))
  const addOption = () => { if (options.length < 4) setOptions(prev => [...prev, '']) }
  const removeOption = (i) => { if (options.length > 2) setOptions(prev => prev.filter((_, idx) => idx !== i)) }

  return (
    <div style={{ marginTop: 12, background: 'var(--bg-hover)', borderRadius: 12, padding: 14 }}>
      <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: 10 }}>📊 Poll</div>
      <input
        placeholder="Poll question…"
        value={poll.question || ''}
        onChange={e => onChange({ ...poll, question: e.target.value, options })}
        style={{ marginBottom: 8 }}
      />
      {options.map((opt, i) => (
        <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
          <input placeholder={`Option ${i + 1}`} value={opt} onChange={e => updateOption(i, e.target.value)} style={{ flex: 1 }} />
          {options.length > 2 && (
            <button onClick={() => removeOption(i)} className="btn btn-ghost btn-icon"><X size={14} /></button>
          )}
        </div>
      ))}
      {options.length < 4 && (
        <button onClick={addOption} className="btn btn-secondary btn-sm" style={{ width: '100%' }}>+ Add Option</button>
      )}
    </div>
  )
}

export default function PostComposer({ onPost }) {
  const { user } = useAuthStore()
  const [content, setContent] = useState('')
  const [visibility, setVisibility] = useState('public')
  const [posting, setPosting] = useState(false)
  const [mediaUrls, setMediaUrls] = useState([])
  const [mediaType, setMediaType] = useState('none')
  const [uploading, setUploading] = useState(false)
  const [showPoll, setShowPoll] = useState(false)
  const [poll, setPoll] = useState({ question: '', options: ['', ''], closesIn: null })
  const [mentionQuery, setMentionQuery] = useState('')
  const [mentionCursorPos, setMentionCursorPos] = useState(null)
  const [mentionStart, setMentionStart] = useState(-1)
  const imageInputRef = useRef(null)
  const videoInputRef = useRef(null)
  const textareaRef = useRef(null)

  const VisibilityIcon = VISIBILITY_ICONS[visibility]
  const charLeft = 5000 - content.length
  const tooLong = charLeft < 0

  // Detect @mention in textarea
  const handleContentChange = (e) => {
    const val = e.target.value
    setContent(val)
    const cursor = e.target.selectionStart
    // Find @ before cursor
    const before = val.slice(0, cursor)
    const atIdx = before.lastIndexOf('@')
    if (atIdx !== -1 && (atIdx === 0 || /\s/.test(before[atIdx - 1]))) {
      const q = before.slice(atIdx + 1)
      if (!q.includes(' ')) {
        setMentionQuery(q)
        setMentionStart(atIdx)
        setMentionCursorPos(atIdx * 8) // approximate pixel pos
        return
      }
    }
    setMentionQuery('')
    setMentionStart(-1)
  }

  const insertMention = (username) => {
    const before = content.slice(0, mentionStart)
    const after = content.slice(textareaRef.current.selectionStart)
    const newContent = `${before}@${username} ${after}`
    setContent(newContent)
    setMentionQuery('')
    setMentionStart(-1)
    textareaRef.current?.focus()
  }

  const handleFileUpload = async (file, type) => {
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post('/chat/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setMediaUrls(prev => [...prev, data.file_url])
      setMediaType(type)
      toast.success('Uploaded!')
    } catch (e) {
      toast.error(e.response?.data?.error || 'Upload failed')
    }
    setUploading(false)
  }

  const removeMedia = (idx) => {
    setMediaUrls(prev => prev.filter((_, i) => i !== idx))
    if (mediaUrls.length <= 1) setMediaType('none')
  }

  // Extract URLs from content for link preview
  const extractUrl = (text) => {
    const m = text.match(/https?:\/\/[^\s]+/)
    return m ? m[0] : null
  }

  const submit = async () => {
    if (!content.trim() && mediaUrls.length === 0 && !showPoll) return
    setPosting(true)
    try {
      const payload = {
        content: content.trim(),
        visibility,
        media: mediaUrls,
        media_type: mediaUrls.length > 0 ? mediaType : 'none',
      }

      // Include poll data if active
      if (showPoll && poll.question && poll.options.filter(o => o.trim()).length >= 2) {
        payload.poll = {
          question: poll.question,
          options: poll.options.filter(o => o.trim()),
        }
      }

      const { data } = await api.post('/posts/', payload)
      onPost?.(data)
      setContent('')
      setMediaUrls([])
      setMediaType('none')
      setShowPoll(false)
      setPoll({ question: '', options: ['', ''], closesIn: null })
      toast.success('Post shared!')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to post')
    }
    setPosting(false)
  }

  return (
    <div className="compose-card">
      <input type="file" accept="image/*" ref={imageInputRef} style={{ display: 'none' }}
        onChange={e => handleFileUpload(e.target.files[0], 'image')} />
      <input type="file" accept="video/*" ref={videoInputRef} style={{ display: 'none' }}
        onChange={e => handleFileUpload(e.target.files[0], 'video')} />

      <div style={{ display: 'flex', gap: 12 }}>
        <div className="avatar avatar-md">
          {user?.avatar_url ? <img src={user.avatar_url} alt="" /> : <span>{user?.username?.[0]?.toUpperCase()}</span>}
        </div>
        <div style={{ flex: 1, position: 'relative' }}>
          <textarea
            ref={textareaRef}
            id="post-composer-textarea"
            className="compose-textarea"
            placeholder={`What's on your mind, ${user?.username?.split(' ')[0]}?`}
            value={content}
            onChange={handleContentChange}
            onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit() }}
            rows={3}
          />
          {mentionQuery !== '' && (
            <MentionAutocomplete query={mentionQuery} onSelect={insertMention} position={mentionCursorPos} />
          )}
        </div>
      </div>

      {/* Media Previews */}
      {mediaUrls.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
          {mediaUrls.map((url, idx) => (
            <div key={idx} style={{ position: 'relative' }}>
              {mediaType === 'image'
                ? <img src={url} alt="" style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 8 }} />
                : <video src={url} style={{ width: 140, height: 100, objectFit: 'cover', borderRadius: 8 }} />
              }
              <button onClick={() => removeMedia(idx)} style={{
                position: 'absolute', top: -6, right: -6, width: 20, height: 20,
                borderRadius: '50%', background: 'var(--danger)', border: 'none',
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}><X size={12} color="white" /></button>
            </div>
          ))}
          {uploading && <div style={{ width: 100, height: 100, borderRadius: 8, background: 'var(--bg-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Loader2 size={20} className="spin" color="var(--primary)" />
          </div>}
        </div>
      )}

      {/* Poll builder */}
      {showPoll && <PollBuilder poll={poll} onChange={setPoll} />}

      {/* Character count */}
      {content.length > 4000 && (
        <div style={{ textAlign: 'right', fontSize: '0.75rem', color: tooLong ? 'var(--danger)' : 'var(--text-muted)', marginTop: 4 }}>
          {charLeft} remaining
        </div>
      )}

      <div className="compose-divider" />

      <div className="compose-actions">
        <div className="compose-media-btns">
          <button className="compose-media-btn" title="Add Image" onClick={() => imageInputRef.current?.click()} disabled={uploading || showPoll}>
            {uploading ? <Loader2 size={18} className="spin" /> : <Image size={18} />}
          </button>
          <button className="compose-media-btn" title="Add Video" onClick={() => videoInputRef.current?.click()} disabled={uploading || showPoll}>
            <Video size={18} />
          </button>
          <button className="compose-media-btn" title="Add Poll" onClick={() => setShowPoll(p => !p)} disabled={mediaUrls.length > 0}
            style={{ color: showPoll ? 'var(--primary)' : undefined }}>
            <BarChart2 size={18} />
          </button>

          {/* Visibility toggle */}
          <button
            className="compose-media-btn"
            title={`Visible to: ${VISIBILITY_LABELS[visibility]}`}
            onClick={() => {
              const order = ['public', 'friends', 'private']
              setVisibility(order[(order.indexOf(visibility) + 1) % order.length])
            }}
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 10px', width: 'auto', borderRadius: 'var(--radius-full)', border: '1px solid var(--border)' }}
          >
            <VisibilityIcon size={14} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{VISIBILITY_LABELS[visibility]}</span>
          </button>
        </div>

        <button
          className="btn btn-primary btn-sm"
          onClick={submit}
          disabled={posting || (!content.trim() && mediaUrls.length === 0 && !showPoll) || tooLong || uploading}
        >
          {posting ? <><Loader2 size={14} className="spin" /> Posting…</> : 'Share Post'}
        </button>
      </div>
    </div>
  )
}
