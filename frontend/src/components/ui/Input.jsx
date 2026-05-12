import styles from './Input.module.css'

export default function Input({
  label, error, icon: Icon, className = '', ...props
}) {
  return (
    <div className={[styles.wrapper, className].join(' ')}>
      {label && <label className={styles.label}>{label}</label>}
      <div className={styles.inputWrap}>
        {Icon && <Icon size={16} className={styles.icon} />}
        <input
          className={[styles.input, Icon ? styles.withIcon : '', error ? styles.hasError : ''].join(' ')}
          {...props}
        />
      </div>
      {error && <span className={styles.error}>{error}</span>}
    </div>
  )
}
