import { MessageSquare, Zap } from 'lucide-react'
import s from './EmptyState.module.css'

export default function EmptyState() {
  return (
    <div className={s.wrap}>
      <div className={s.icon}>
        <MessageSquare size={36} strokeWidth={1.5} />
      </div>
      <h2 className={s.title}>Your conversations</h2>
      <p className={s.sub}>Select a chat from the sidebar or start a new one.</p>
      <div className={s.hint}>
        <Zap size={12} />
        <span>Press <kbd>N</kbd> to start a new conversation</span>
      </div>
    </div>
  )
}
