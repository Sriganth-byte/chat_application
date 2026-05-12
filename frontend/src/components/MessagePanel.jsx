import React, { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Hash, Phone, Video, MoreHorizontal, Paperclip, Send, Smile, Reply, Edit2, Trash2, X, Check, CheckCheck, Mic, Eye, EyeOff, Share2, Download, MicOff, VideoOff } from 'lucide-react'
import { toast } from 'react-hot-toast'
import useChatStore from '../store/chatStore'
import useAuthStore from '../store/authStore'
import { useWebSocket } from '../hooks/useWebSocket'
import Avatar from './ui/Avatar'
import api from '../api/axios'
import s from './MessagePanel.module.css'
import { format, isToday, isYesterday } from 'date-fns'

export default function MessagePanel({ isMobile, onBack }) {
  const { activeRoom } = useChatStore()

  if (!activeRoom) {
    return (
      <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100%',color:'white'}}>
        Select a chat to start messaging
      </div>
    )
  }

  return <MessagePanelInner isMobile={isMobile} onBack={onBack} />
}

function MessagePanelInner({ isMobile, onBack }) {
  const store = useChatStore()
  const activeRoom = store.activeRoom
  const messages = store.messages || {}
  const typingUsers = store.typingUsers || {}
  const pendingAcceptedCall = store.pendingAcceptedCall
  const callAnswer = store.callAnswer
  const iceCandidates = store.iceCandidates || []
  const activeCall = store.activeCall
  const callEndedAt = store.callEndedAt
  const fetchMessages = store.fetchMessages || (() => {})
  const updateMessage = store.updateMessage || (() => {})
  const removeMessage = store.removeMessage || (() => {})
  const setActiveCall = store.setActiveCall || (() => {})
  const clearIceCandidates = store.clearIceCandidates || (() => {})
  const clearPendingAcceptedCall = store.clearPendingAcceptedCall || (() => {})
  const clearCall = store.clearCall || (() => {})

  const user = useAuthStore().user
  // useWebSocket must always be called (no conditional) — it guards roomId internally
  const ws = useWebSocket(activeRoom?.id)
  const send = ws?.send || (() => {})
  const callSocketReady = Boolean(ws?.isOpen)

  const [text, setText] = useState('')
  const [replyTo, setReplyTo] = useState(null)
  const [editMsg, setEditMsg] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [oneTime, setOneTime] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [callActive, setCallActive] = useState(false)
  const [callType, setCallType] = useState(null)
  // Separate local (mic/camera) from remote (what the other person sends)
  const [localStream, setLocalStream] = useState(null)
  const [remoteStream, setRemoteStream] = useState(null)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const typingTimer = useRef(null)
  const fileRef = useRef(null)
  const recorderRef = useRef(null)
  const localStreamRef = useRef(null)
  const localVideoRef = useRef(null)   // local camera preview
  const remoteVideoRef = useRef(null)  // remote video feed
  const remoteAudioRef = useRef(null)  // remote audio (voice call)
  // Tracks the remote peer's user ID so ICE candidates can be targeted
  const activeCallRef = useRef(null)
  const remoteUserRef = useRef(null)
  const remoteStreamRef = useRef(null)
  const pendingIceCandidatesRef = useRef([])

  const roomId = activeRoom?.id
  const key = String(roomId)
  const roomMessages = Array.isArray(messages[key]) ? messages[key] : []
  // typingUsers[key] is an object keyed by userId, not an array
  const typing = (typingUsers[key] && typeof typingUsers[key] === 'object')
    ? Object.values(typingUsers[key])
    : []

  useEffect(() => {
    if (roomId) {
      fetchMessages(roomId)
    }
  }, [roomId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [roomMessages.length])

  useEffect(() => {
    return () => {
      if (recorderRef.current) recorderRef.current.stop()
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach(t => t.stop())
      }
    }
  }, [])

  // Wire local camera preview
  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream
    }
  }, [localStream])

  // Wire remote video feed
  useEffect(() => {
    if (remoteVideoRef.current && remoteStream) {
      remoteVideoRef.current.srcObject = remoteStream
      remoteVideoRef.current.muted = true
      remoteVideoRef.current.play?.().catch(() => {})
    }
  }, [remoteStream])

  // Wire remote audio (voice calls — no video element needed)
  useEffect(() => {
    if (remoteAudioRef.current && remoteStream) {
      remoteAudioRef.current.srcObject = remoteStream
      remoteAudioRef.current.play?.().catch(() => {})
    }
  }, [remoteStream])

  useEffect(() => {
    if (!pendingAcceptedCall?.offer) return
    if (String(pendingAcceptedCall.roomId) !== String(roomId)) return
    if (!callSocketReady) return
    handleIncomingCall(pendingAcceptedCall)
    clearPendingAcceptedCall()
  }, [pendingAcceptedCall, roomId, callSocketReady])

  useEffect(() => {
    let cancelled = false

    async function applyAnswer() {
      if (!callAnswer?.answer || !activeCall) return
      try {
        // Store the callee's user ID so ICE candidates are targeted to them
        if (callAnswer.fromUser) remoteUserRef.current = callAnswer.fromUser
        if (!activeCall.remoteDescription) {
          await activeCall.setRemoteDescription(new RTCSessionDescription(callAnswer.answer))
        }
        if (!cancelled) {
          await flushPendingIceCandidates(activeCall)
        }
      } catch (err) {
        console.error('setRemoteDescription error:', err)
      }
    }

    applyAnswer()
    return () => { cancelled = true }
  }, [callAnswer, activeCall])

  useEffect(() => {
    let cancelled = false

    async function applyCandidates() {
      if (!iceCandidates.length) return
      pendingIceCandidatesRef.current.push(...iceCandidates.filter(item => item?.candidate))
      clearIceCandidates()

      if (!cancelled && activeCall?.remoteDescription) {
        await flushPendingIceCandidates(activeCall)
      }
    }

    applyCandidates()
    return () => { cancelled = true }
  }, [iceCandidates, activeCall])

  useEffect(() => {
    if (callEndedAt && callActive) {
      endCall(false)
    }
  }, [callEndedAt])

  const getRtcIceServers = () => {
    const configured = import.meta.env.VITE_RTC_ICE_SERVERS
    if (configured) {
      try {
        const parsed = JSON.parse(configured)
        if (Array.isArray(parsed) && parsed.length) return parsed
      } catch (err) {
        console.warn('Invalid VITE_RTC_ICE_SERVERS value:', err)
      }
    }

    return [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
      { urls: 'stun:stun2.l.google.com:19302' },
      { urls: 'stun:stun3.l.google.com:19302' },
    ]
  }

  const createCallPeerConnection = (targetUser) => {
    const pc = new RTCPeerConnection({ iceServers: getRtcIceServers() })

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        try {
          send({
            type: 'call_ice',
            candidate: event.candidate.toJSON ? event.candidate.toJSON() : event.candidate,
            target_user: targetUser || remoteUserRef.current,
          })
        } catch (err) {
          console.warn('Unable to send ICE candidate:', err)
        }
      }
    }

    pc.ontrack = (event) => {
      const existingStream = remoteStreamRef.current || new MediaStream()
      const previousTracks = existingStream.getTracks()
      const incomingTracks = event.streams?.[0]?.getTracks() || (event.track ? [event.track] : [])
      const tracksById = new Map(previousTracks.map(track => [track.id, track]))

      incomingTracks.forEach(track => tracksById.set(track.id, track))

      const nextStream = new MediaStream([...tracksById.values()])
      remoteStreamRef.current = nextStream
      setRemoteStream(nextStream)
    }

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'failed') {
        toast.error('Call connection failed. Try again or configure a TURN server for external networks.')
      }
    }

    return pc
  }

  async function flushPendingIceCandidates(pc) {
    if (!pc?.remoteDescription || pendingIceCandidatesRef.current.length === 0) return

    const pending = pendingIceCandidatesRef.current
    pendingIceCandidatesRef.current = []

    for (const item of pending) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(item.candidate))
        if (item.fromUser) remoteUserRef.current = item.fromUser
      } catch (err) {
        console.error('addIceCandidate error:', err)
      }
    }
  }

  function waitForIceGatheringComplete(pc, timeoutMs = 3000) {
    if (!pc || pc.iceGatheringState === 'complete') {
      return Promise.resolve()
    }

    return new Promise(resolve => {
      let settled = false
      const done = () => {
        if (settled) return
        settled = true
        clearTimeout(timer)
        pc.removeEventListener('icegatheringstatechange', onStateChange)
        resolve()
      }
      const onStateChange = () => {
        if (pc.iceGatheringState === 'complete') {
          done()
        }
      }
      const timer = setTimeout(done, timeoutMs)

      pc.addEventListener('icegatheringstatechange', onStateChange)
    })
  }

  const handleIncomingCall = async (call) => {
    if (!call || !call.offer) {
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error('Camera/microphone not available. Open the app via HTTPS or localhost.')
      return
    }
    try {
      const isVideoCall = call.callType === 'video' || /\bm=video\b/i.test(call.offer?.sdp || '')
      const constraints = isVideoCall
        ? { audio: true, video: true }
        : { audio: true }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      localStreamRef.current = stream
      setLocalStream(stream)   // show local preview

      remoteUserRef.current = call.fromUser
      const pc = createCallPeerConnection(call.fromUser)

      stream.getTracks().forEach(track => pc.addTrack(track, stream))

      // Remote tracks arrive here — set as the remote stream
      await pc.setRemoteDescription(new RTCSessionDescription(call.offer))
      await flushPendingIceCandidates(pc)
      const answer = await pc.createAnswer()
      await pc.setLocalDescription(answer)
      await waitForIceGatheringComplete(pc)

      try {
        send({
          type: 'call_answer',
          answer: pc.localDescription?.toJSON ? pc.localDescription.toJSON() : pc.localDescription,
          target_user: call.fromUser,
        })
      } catch (err) {
        console.warn('Unable to send call answer:', err)
      }

      setActiveCall(pc)
      activeCallRef.current = pc
      setCallType(isVideoCall ? 'video' : 'voice')
      setCallActive(true)
    } catch (err) {
      console.error('handleIncomingCall error:', err)
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        toast.error('Microphone/camera permission denied. Allow access in your browser settings.')
      } else if (err.name === 'NotFoundError') {
        toast.error('No microphone found. Please connect a microphone and try again.')
      } else if (err.name === 'NotReadableError') {
        toast.error('Microphone is in use by another app.')
      } else {
        toast.error('Unable to join call. Check microphone permissions.')
      }
    }
  }


  const handleTyping = () => {
    send({ type: 'typing_start' })
    clearTimeout(typingTimer.current)
    typingTimer.current = setTimeout(() => send({ type: 'typing_stop' }), 2000)
  }

  const submitMessage = async (e) => {
    e?.preventDefault()
    const content = text.trim()
    if (!content) return

    try {
      if (editMsg && editMsg.id) {
        try { send({ type: 'message_edit', message_id: editMsg.id, content }) } catch(e) {}
        if (activeRoom?.id) updateMessage(activeRoom.id, { ...editMsg, content, edited: true })
        setEditMsg(null)
      } else {
        try {
          send({
            type: 'message',
            content,
            message_type: 'text',
            reply_to_id: replyTo?.id || null,
            one_time: oneTime,
          })
        } catch(e) {}
        setReplyTo(null)
      }
      setText('')
      try { send({ type: 'typing_stop' }) } catch(e) {}
      if (typingTimer.current) clearTimeout(typingTimer.current)
    } catch (err) {
      console.error('submitMessage error:', err)
    }
  }

  const handleFile = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await api.post('/chat/upload/', fd)
      send({
        type: 'message',
        content: data.file_url,
        message_type: data.message_type,
        one_time: oneTime,
        file_name: data.file_name,
      })
      toast.success('File sent')
    } catch (err) {
      console.error('File upload error:', err)
      toast.error(err.response?.data?.error || 'Failed to upload file')
    }
    setUploading(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitMessage() }
  }

  const startEdit = (msg) => {
    setEditMsg(msg)
    setText(msg.content)
    setReplyTo(null)
    inputRef.current?.focus()
  }

  const copyToClipboard = async (value) => {
    try {
      await navigator.clipboard.writeText(value)
      toast.success('Link copied to clipboard')
    } catch {
      toast.error('Unable to copy link')
    }
  }

  const consumeMessage = (msg) => {
    if (!msg.one_time || msg.one_time_consumed) return
    send({ type: 'message_consume', message_id: msg.id })
  }

  const openCall = async (type) => {
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        toast.error('Media devices not available. Open the app via HTTPS.')
        return
      }
      const constraints = type === 'video'
        ? { audio: true, video: true }
        : { audio: true }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      localStreamRef.current = stream
      setLocalStream(stream)   // local preview
      setCallType(type)
      setCallActive(true)

      const pc = createCallPeerConnection()

      stream.getTracks().forEach(track => pc.addTrack(track, stream))

      // Remote tracks arrive here — set as the remote stream to play audio/video
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      await waitForIceGatheringComplete(pc)

      try {
        send({
          type: 'call_offer',
          offer: pc.localDescription?.toJSON ? pc.localDescription.toJSON() : pc.localDescription,
          call_type: type,
        })
      } catch (err) {
        console.warn('Unable to send call offer:', err)
      }
      activeCallRef.current = pc
      setActiveCall(pc)

    } catch (err) {
      console.error('Call error:', err)
      toast.error('Unable to access microphone/camera')
      setCallActive(false)
    }
  }

  function endCall(notifyPeer = true) {
    try {
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach(t => t.stop())
        localStreamRef.current = null
      }
      if (remoteStream) {
        remoteStream.getTracks().forEach(t => t.stop())
      }
      remoteStreamRef.current = null
      const callToClose = activeCall || activeCallRef.current
      if (callToClose) {
        try { callToClose.close() } catch(e) {}
        activeCallRef.current = null
        setActiveCall(null)
      }
      setLocalStream(null)
      setRemoteStream(null)
      setCallActive(false)
      setCallType(null)
      remoteUserRef.current = null
      pendingIceCandidatesRef.current = []
      clearCall()
      if (notifyPeer) {
        try {
          send({ type: 'call_end' })
        } catch (err) {
          console.warn('Unable to send call end:', err)
        }
      }
    } catch (err) {
      console.error('endCall error:', err)
    }
  }

  const startRecording = async () => {
    if (isRecording) {
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error('Browser does not support audio recording')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      const chunksRef = { current: [] }
      const streamRef = { current: stream }

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
      })

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = async () => {
        setIsRecording(false)
        setUploading(true)

        try {
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
          const extension = recorder.mimeType?.includes('mp4') ? 'm4a' : 'webm'
          const file = new File([blob], `voice-message.${extension}`, { type: recorder.mimeType || 'audio/webm' })

          const fd = new FormData()
          fd.append('file', file)

          const { data } = await api.post('/chat/upload/', fd)
          send({
            type: 'message',
            content: data.file_url,
            message_type: data.message_type,
            one_time: oneTime,
            file_name: data.file_name || `Voice message.${extension}`,
          })
          toast.success('Voice message sent')
        } catch (err) {
          console.error('Voice upload error:', err)
          toast.error(err.response?.data?.error || 'Voice message upload failed')
        }

        setUploading(false)
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop())
        }
      }

      recorder.start(1000)
      recorderRef.current = recorder
      localStreamRef.current = stream
      setIsRecording(true)
      toast.success('Recording... click mic to stop')
    } catch (err) {
      console.error('Recording error:', err)
      toast.error('Could not start recording. Please check microphone permissions.')
    }
  }

  const stopRecording = () => {
    if (!isRecording) return
    recorderRef.current?.stop()
  }

  const cancelEdit = () => { setEditMsg(null); setText('') }

  const deleteMsg = (msg) => {
    send({ type: 'message_delete', message_id: msg.id })
    removeMessage(activeRoom.id, msg.id)
  }

  const isGroup = activeRoom?.type === 'group'
  const members = Array.isArray(activeRoom?.members) ? activeRoom.members : []
  const otherMember = !isGroup
    ? members.find(m => m && m.user && m.user.id !== user?.id)?.user
    : null

  const headerName = isGroup ? (activeRoom?.name || 'Group') : (otherMember?.username || 'Chat')
  const headerSub  = isGroup
    ? `${members.length} members`
    : (otherMember?.is_online ? 'Online' : 'Offline')

  return (
    <div className={s.panel}>

      {/* ── Header ── */}
      <div className={s.header}>
        <div className={s.headerLeft}>
          {isMobile && onBack && (
            <button className={s.backBtn} type="button" onClick={onBack} title="Back to chats">
              <ArrowLeft size={16} />
            </button>
          )}
          {isGroup
            ? <div className={s.groupAvatar}><Hash size={18} /></div>
            : <Avatar name={otherMember?.username || ''} size="md" online={otherMember?.is_online} />
          }
          <div className={s.headerInfo}>
            <span className={s.headerName}>{headerName}</span>
            <span className={[s.headerSub, otherMember?.is_online ? s.online : ''].join(' ')}>
              {headerSub}
            </span>
          </div>
        </div>
        <div className={s.headerActions}>
          <button className={s.hBtn} title="Voice call" onClick={() => openCall('voice')}><Phone size={16} /></button>
          <button className={s.hBtn} title="Video call" onClick={() => openCall('video')}><Video size={16} /></button>
          <button className={s.hBtn} title="More"><MoreHorizontal size={16} /></button>
        </div>
      </div>

      {/* ── Messages ── */}
      <div className={s.messages}>
        {roomMessages.length === 0 && (
          <div className={s.emptyChat}>
            <div className={s.emptyChatIcon}>
              {isGroup ? <Hash size={32} strokeWidth={1.5} /> : <Smile size={32} strokeWidth={1.5} />}
            </div>
            <p className={s.emptyChatTitle}>Start the conversation</p>
            <p className={s.emptyChatSub}>
              {isGroup ? `Say hello to ${headerName}` : `Send ${headerName} a message`}
            </p>
          </div>
        )}

        {(() => {
          if (!Array.isArray(roomMessages) || roomMessages.length === 0) {
            return <div style={{padding:40,textAlign:'center',color:'white'}}>No messages yet</div>
          }
          return roomMessages.map((msg) => {
            if (!msg || !msg.id) return null
            return (
              <MessageRow
                key={msg.id}
                msg={msg}
                isMine={msg.sender?.id === user?.id}
                onReply={() => setReplyTo(msg)}
                onEdit={() => startEdit(msg)}
                onDelete={() => deleteMsg(msg)}
                onConsume={consumeMessage}
                onCopy={copyToClipboard}
              />
            )
          })
        })()}

        {/* Typing indicator */}
        {typing.length > 0 && (
          <div className={s.typingRow}>
            <div className={s.typingBubble}>
              <span className={s.typingDots}>
                <span /><span /><span />
              </span>
              <span className={s.typingText}>
                {typing.join(', ')} {typing.length === 1 ? 'is' : 'are'} typing
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Reply / Edit bar ── */}
      {(replyTo || editMsg) && (
        <div className={s.contextBar}>
          <div className={s.contextIcon}>
            {editMsg ? <Edit2 size={13} /> : <Reply size={13} />}
          </div>
          <div className={s.contextText}>
            <span className={s.contextLabel}>{editMsg ? 'Editing message' : `Replying to ${replyTo?.sender?.username}`}</span>
            <span className={s.contextPreview}>
              {(editMsg || replyTo)?.content?.slice(0, 60)}
            </span>
          </div>
          <button className={s.contextClose} onClick={() => { setReplyTo(null); cancelEdit() }}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* ── Input bar ── */}
      <div className={s.inputBar}>
        <input ref={fileRef} type="file" hidden onChange={handleFile}
          accept=".jpg,.jpeg,.png,.webp,.pdf,.mp3,.wav,.mp4,.mov,.webm,.ogg" />
        <button className={s.attachBtn} onClick={() => fileRef.current?.click()} disabled={uploading}>
          <Paperclip size={17} />
        </button>
        <button
          className={[s.attachBtn, oneTime ? s.oneTimeActive : ''].join(' ')}
          onClick={() => setOneTime(prev => !prev)}
          title={oneTime ? 'One-time media is active' : 'Enable one-time media'}
          type="button"
        >
          {oneTime ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
        <button
          className={[s.attachBtn, isRecording ? s.recording : ''].join(' ')}
          onClick={() => (isRecording ? stopRecording() : startRecording())}
          title={isRecording ? 'Stop recording' : 'Record voice message'}
          type="button"
          disabled={uploading}
        >
          <Mic size={17} />
        </button>
        <div className={s.inputWrap}>
          <textarea
            ref={inputRef}
            className={s.input}
            placeholder={`Message ${headerName}…`}
            value={text}
            onChange={e => { setText(e.target.value); handleTyping() }}
            onKeyDown={handleKey}
            rows={1}
          />
        </div>
        <button
          className={[s.sendBtn, text.trim() ? s.sendActive : ''].join(' ')}
          onClick={submitMessage}
          disabled={!text.trim() && !uploading}
        >
          <Send size={16} strokeWidth={2.5} />
        </button>
      </div>
      {callActive && (
        <CallModal
          open={callActive}
          type={callType}
          localStream={localStream}
          remoteStream={remoteStream}
          localVideoRef={localVideoRef}
          remoteVideoRef={remoteVideoRef}
          remoteAudioRef={remoteAudioRef}
          onClose={endCall}
        />
      )}
    </div>
  )
}

/* ── Message row ── */
const MESSAGE_WINDOW_MS = 15 * 60 * 1000 // 15 minutes

function MessageRow({ msg, isMine, grouped, onReply, onEdit, onDelete, onConsume, onCopy }) {
  // Keep useState unconditionally before any early return (rules of hooks)
  const [hover, setHover] = useState(false)

  if (!msg) return null

  const messageType = msg.message_type || 'text'
  const isFile = messageType !== 'text'
  const age = msg.created_at ? Date.now() - new Date(msg.created_at).getTime() : Infinity
  const canManage = isMine && age < MESSAGE_WINDOW_MS

  return (
    <div
      className={[s.msgRow, isMine ? s.mine : '', grouped ? s.grouped : ''].join(' ')}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {!isMine && (
        <div className={s.msgAvatar}>
          {!grouped
            ? <Avatar name={msg.sender?.username || ''} size="sm" />
            : <div className={s.avatarSpacer} />
          }
        </div>
      )}

      <div className={s.msgContent}>
        {!grouped && !isMine && (
          <span className={s.msgSender}>{msg.sender?.username}</span>
        )}

        {msg.reply_to_data && (
          <div className={s.replyRef}>
            <span className={s.replyRefName}>{msg.reply_to_data.sender}</span>
            <span className={s.replyRefText}>{msg.reply_to_data.content}</span>
          </div>
        )}

        <div className={[s.bubble, isMine ? s.bubbleMine : s.bubbleTheirs].join(' ')}>
          {isFile
            ? <FileContent msg={msg} onConsume={onConsume} onCopy={onCopy} />
            : <span className={s.msgText}>{msg.content}</span>
          }
          {msg.one_time && <div className={s.oneTimeBadge}>{msg.one_time_consumed ? 'Consumed' : 'View once'}</div>}
          <div className={s.msgMeta}>
            <span className={s.msgTime}>
              {msg.created_at ? format(new Date(msg.created_at), 'HH:mm') : ''}
            </span>
            {msg.edited && <span className={s.edited}>edited</span>}
            {isMine && (
              <span className={s.seenIcon}>
                {msg.is_seen ? <CheckCheck size={12} /> : <Check size={12} />}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Hover actions */}
      {hover && (
        <div className={[s.actions, isMine ? s.actionsLeft : s.actionsRight].join(' ')}>
          <button className={s.actionBtn} onClick={onReply} title="Reply"><Reply size={13} /></button>
          {canManage && <button className={s.actionBtn} onClick={onEdit} title="Edit"><Edit2 size={13} /></button>}
          {canManage && <button className={[s.actionBtn, s.actionDanger].join(' ')} onClick={onDelete} title="Delete"><Trash2 size={13} /></button>}
        </div>
      )}
    </div>
  )
}

function FileContent({ msg, onConsume, onCopy }) {
  const [revealed, setRevealed] = useState(false)
  const [consumed, setConsumed] = useState(false)
  const [audioDuration, setAudioDuration] = useState(null)

  const isOneTime = msg?.one_time === true
  const isConsumed = msg?.one_time_consumed === true

  // Sync consumed/revealed state when msg props change
  useEffect(() => {
    setConsumed(isConsumed)
    setRevealed(!isOneTime)
  }, [isConsumed, isOneTime])

  if (!msg) return null

  const handleReveal = () => {
    if (isOneTime && !isConsumed) {
      onConsume?.(msg)
    }
    setRevealed(true)
  }

  const formatDuration = (seconds) => {
    if (!seconds || Number.isNaN(seconds)) return '0:00'
    const whole = Math.max(0, Math.round(seconds))
    const mins = Math.floor(whole / 60)
    const secs = whole % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Resolve the media src: prefer content (legacy absolute or new relative URL),
  // fall back to file_url which the serializer also returns.
  const mediaSrc = msg.content || msg.file_url || null
  const handleCopy = () => {
    if (mediaSrc) onCopy?.(mediaSrc)
  }

  const downloadName = msg.file_name || `media-${msg.id}`
  const messageType = msg.message_type || 'file'

  if (isOneTime && consumed && !revealed) {
    return (
      <div className={s.oneTimePlaceholder}>
        <span>One-time media consumed</span>
      </div>
    )
  }

  if (isOneTime && !revealed) {
    return (
      <button className={s.oneTimeAction} onClick={handleReveal} type="button">
        <Eye size={14} />
        <span>View once</span>
      </button>
    )
  }

  if (messageType === 'image') {
    if (!mediaSrc) return null
    return (
      <div className={s.filePreview}>
        <img src={mediaSrc} alt="image" className={s.imgMsg} onError={(e) => { e.target.style.display = 'none' }} />
        <div className={s.mediaActions}>
          <a href={mediaSrc} target="_blank" rel="noreferrer" download={downloadName} className={s.mediaAction}>
            <Download size={14} />
          </a>
          <button className={s.mediaAction} type="button" onClick={handleCopy}>
            <Share2 size={14} />
          </button>
        </div>
      </div>
    )
  }

  if (messageType === 'audio') {
    if (!mediaSrc) return null

    return (
      <div className={s.filePreview}>
        <div className={s.audioWrapper}>
          <div className={s.audioHeader}>
            <span className={s.audioBadge}>Voice message</span>
            <span className={s.audioDuration}>{formatDuration(audioDuration)}</span>
          </div>
          <audio
            controls
            src={mediaSrc}
            className={s.audioPlayer}
            onLoadedMetadata={(e) => {
              const duration = e.target.duration
              if (!Number.isNaN(duration)) setAudioDuration(duration)
            }}
            onPlay={() => isOneTime && !isConsumed && handleReveal()}
          />
        </div>
        <div className={s.mediaActions}>
          <a href={mediaSrc} target="_blank" rel="noreferrer" download={downloadName} className={s.mediaAction}>
            <Download size={14} />
          </a>
          <button className={s.mediaAction} type="button" onClick={handleCopy}>
            <Share2 size={14} />
          </button>
        </div>
      </div>
    )
  }

  if (messageType === 'video') {
    if (!mediaSrc) return null
    return (
      <div className={s.filePreview}>
        <video
          controls
          src={mediaSrc}
          className={s.videoPlayer}
          onPlay={() => isOneTime && !isConsumed && handleReveal()}
        />
        <div className={s.mediaActions}>
          <a href={mediaSrc} target="_blank" rel="noreferrer" download={downloadName} className={s.mediaAction}>
            <Download size={14} />
          </a>
          <button className={s.mediaAction} type="button" onClick={handleCopy}>
            <Share2 size={14} />
          </button>
        </div>
      </div>
    )
  }

  if (!mediaSrc) return null
  return (
    <div className={s.filePreview}>
      <a href={mediaSrc} target="_blank" rel="noreferrer" download={downloadName} className={s.fileMsg}>
        <Paperclip size={14} />
        <span>{msg.file_name || 'Download file'}</span>
      </a>
      <div className={s.mediaActions}>
        <button className={s.mediaAction} type="button" onClick={handleCopy}>
          <Share2 size={14} />
        </button>
      </div>
    </div>
  )
}

function CallModal({ open, type, localStream, remoteStream, localVideoRef, remoteVideoRef, remoteAudioRef, onClose }) {
  const [muted, setMuted] = useState(false)
  const [videoOff, setVideoOff] = useState(false)

  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream
      localVideoRef.current.play?.().catch(() => {})
    }
  }, [localStream, localVideoRef])

  useEffect(() => {
    if (remoteVideoRef.current && remoteStream) {
      remoteVideoRef.current.srcObject = remoteStream
      remoteVideoRef.current.muted = true
      remoteVideoRef.current.play?.().catch(() => {})
    }
  }, [remoteStream, remoteVideoRef])

  useEffect(() => {
    if (remoteAudioRef.current && remoteStream) {
      remoteAudioRef.current.srcObject = remoteStream
      remoteAudioRef.current.play?.().catch(() => {})
    }
  }, [remoteStream, remoteAudioRef])

  if (!open) return null

  const toggleMute = () => {
    // Mute/unmute the LOCAL microphone track — not the remote stream
    if (localStream) {
      localStream.getAudioTracks().forEach(track => {
        track.enabled = muted  // muted=true means currently muted, so re-enable
      })
      setMuted(!muted)
    }
  }

  const toggleVideo = () => {
    // Enable/disable the LOCAL camera track
    if (localStream) {
      localStream.getVideoTracks().forEach(track => {
        track.enabled = videoOff
      })
      setVideoOff(!videoOff)
    }
  }

  return (
    <div className={s.callOverlay}>
      {/*
        Hidden audio element — outputs the REMOTE audio stream.
        This is the critical element for voice calls: without it the remote
        audio has nowhere to play even when WebRTC delivers the track.
        For video calls the remote audio is also included in remoteVideoRef's
        srcObject, but this element acts as a guaranteed fallback.
      */}
      <audio
        ref={remoteAudioRef}
        autoPlay
        playsInline
        style={{ position: 'absolute', width: 1, height: 1, opacity: 0, pointerEvents: 'none' }}
      />

      <div className={s.callWindow}>
        <div className={s.callHeader}>
          <span>{type === 'video' ? 'Video call' : 'Voice call'}</span>
          <button className={s.callClose} type="button" onClick={onClose}><X size={16} /></button>
        </div>
        <div className={s.callBody}>
          {type === 'video' ? (
            <div className={s.videoStage}>
              {/* Remote video — main view */}
              <video
                ref={remoteVideoRef}
                className={s.callVideo}
                autoPlay
                playsInline
                muted
              />
              {!remoteStream?.getVideoTracks?.().length && (
                <div className={s.remoteWaiting}>
                  <Video size={34} />
                  <span>Connecting video...</span>
                </div>
              )}
              {/* Local camera — picture-in-picture overlay */}
              <video
                ref={localVideoRef}
                className={s.localPreview}
                autoPlay
                playsInline
                muted
              />
            </div>
          ) : (
            <div className={s.callAudioPreview}>
              <Phone size={48} />
              <span>{remoteStream ? 'Connected' : 'Calling…'}</span>
            </div>
          )}
          <div className={s.callControls}>
            <button className={s.callControl} type="button" onClick={toggleMute}>
              {muted ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
            {type === 'video' && (
              <button className={s.callControl} type="button" onClick={toggleVideo}>
                {videoOff ? <VideoOff size={20} /> : <Video size={20} />}
              </button>
            )}
            <button className={[s.callControl, s.callEnd].join(' ')} type="button" onClick={onClose}>
              <Phone size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


function groupByDate(msgs) {
  if (!Array.isArray(msgs) || msgs.length === 0) return []
  const groups = {}
  msgs.forEach(m => {
    if (!m || !m.created_at) return
    try {
      const d = new Date(m.created_at)
      if (isNaN(d.getTime())) return
      const key = isToday(d) ? 'Today' : isYesterday(d) ? 'Yesterday' : format(d, 'MMMM d, yyyy')
      if (!groups[key]) groups[key] = []
      groups[key].push(m)
    } catch (e) {
      console.warn('Error parsing message date:', e)
    }
  })
  return Object.entries(groups).map(([date, msgs]) => ({ date, msgs }))
}

function SimpleMessageRow({ msg, isMine }) {
  if (!msg) return null
  const senderName = msg.sender?.username || 'Unknown'
  const content = msg.content || ''
  const msgType = msg.message_type || 'text'
  const time = msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''

  return (
    <div style={{
      display: 'flex',
      flexDirection: isMine ? 'row-reverse' : 'row',
      alignItems: 'flex-start',
      gap: 8,
      padding: '8px 16px'
    }}>
      <div style={{
        width: 32,
        height: 32,
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #7c3aed, #2563eb)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontSize: 12,
        fontWeight: 600,
        flexShrink: 0
      }}>
        {senderName.charAt(0).toUpperCase()}
      </div>
      <div style={{ maxWidth: '70%' }}>
        {!isMine && <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2 }}>{senderName}</div>}
        {msgType === 'image' && content ? (
          <img src={content} alt="image" style={{ maxWidth: 250, borderRadius: 12 }} />
        ) : msgType === 'video' && content ? (
          <video src={content} controls style={{ maxWidth: 250, borderRadius: 12 }} />
        ) : msgType === 'audio' && content ? (
          <audio src={content} controls style={{ maxWidth: 200 }} />
        ) : (
          <div style={{
            background: isMine ? 'rgba(124,58,237,0.2)' : '#1e293b',
            padding: '10px 14px',
            borderRadius: 16,
            color: '#f8fafc',
            fontSize: 14
          }}>
            {content}
          </div>
        )}
        <div style={{ fontSize: 10, color: '#64748b', marginTop: 2, textAlign: isMine ? 'right' : 'left' }}>{time}</div>
      </div>
    </div>
  )
}
