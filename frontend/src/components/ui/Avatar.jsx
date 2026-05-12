import styles from './Avatar.module.css'

export default function Avatar({ src, name = '', size = 'md', online, className = '' }) {
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const colors = ['#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#3b82f6','#ef4444']
  const color = colors[name.charCodeAt(0) % colors.length] || '#6366f1'

  return (
    <div className={[styles.wrap, styles[size], className].join(' ')}>
      {src
        ? <img src={src} alt={name} className={styles.img} />
        : <span className={styles.initials} style={{ background: color }}>{initials || '?'}</span>
      }
      {online !== undefined && (
        <span className={[styles.dot, online ? styles.online : styles.offline].join(' ')} />
      )}
    </div>
  )
}
