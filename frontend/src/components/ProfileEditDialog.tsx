import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Profile, User, ExperienceLevel } from '../types'
import type { ProfileUpdatePayload } from '../api/profile'
import { formatPhoneInput, normalizePhone } from '../utils/phone'

interface ProfileEditDialogProps {
  open: boolean
  onClose: () => void
  user: User | null
  profile: Profile
  onSubmit: (payload: ProfileUpdatePayload) => Promise<void>
  submitting: boolean
  error?: string | null
}

const levelOptions: Array<{ value: ExperienceLevel; label: string; description: string }> = [
  { value: 'newbie', label: 'Новичок', description: 'Спокойный старт и адаптация привычек.' },
  { value: 'enthusiast', label: 'Энтузиаст', description: 'Ускоренный прогресс с еженедельным анализом.' },
  { value: 'pro', label: 'Профи', description: 'Детальный контроль и расширенная аналитика.' },
  { value: 'legend', label: 'Легенда', description: 'Максимум данных и совместная работа с экспертами.' }
]

function ensureModalRoot(): HTMLElement {
  const existing = document.getElementById('modal-root')
  if (existing) return existing
  const element = document.createElement('div')
  element.setAttribute('id', 'modal-root')
  document.body.appendChild(element)
  return element
}

export default function ProfileEditDialog({
  open,
  onClose,
  user,
  profile,
  onSubmit,
  submitting,
  error
}: ProfileEditDialogProps){
  const [lastName, setLastName] = useState('')
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>('newbie')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setLastName(user?.last_name ?? '')
    setFirstName(user?.first_name ?? '')
    setMiddleName(profile.middle_name ?? '')
    setEmail(user?.email ?? '')
    setPhone(formatPhoneInput(user?.username ?? ''))
    setExperienceLevel(profile.experience_level ?? 'newbie')
    setPassword('')
    setPasswordConfirm('')
    setFormError(null)
  }, [open, profile, user])

  const modalRoot = useMemo(() => (typeof document !== 'undefined' ? ensureModalRoot() : null), [])

  if (!open || !modalRoot) {
    return null
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFormError(null)

    if (password && password !== passwordConfirm) {
      setFormError('Пароли не совпадают')
      return
    }

    if (!phone.trim()) {
      setFormError('Укажите номер телефона')
      return
    }

    const normalizedPhone = normalizePhone(phone)
    if (normalizedPhone.length !== 12) {
      setFormError('Введите корректный номер телефона')
      return
    }

    const payload: ProfileUpdatePayload = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      middle_name: middleName.trim(),
      email: email.trim(),
      phone: normalizedPhone,
      experience_level: experienceLevel
    }

    if (password) {
      payload.password = password
    }

    await onSubmit(payload)
  }

  const combinedError = formError || error || null

  return createPortal(
    <div className="profile-edit-dialog" role="dialog" aria-modal="true" aria-labelledby="profile-edit-title">
      <div className="profile-edit-dialog__backdrop" onClick={onClose} />
      <div className="profile-edit-dialog__content">
        <div className="profile-edit-dialog__header">
          <h2 id="profile-edit-title">Редактирование профиля</h2>
          <button type="button" className="profile-edit-dialog__close" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <p className="profile-edit-dialog__hint">
          Обновите контактные данные, уровень программы и пароль. Изменения сохраняются мгновенно.
        </p>
        {combinedError && <div className="profile-edit-dialog__error">{combinedError}</div>}
        <form className="profile-edit-dialog__form" onSubmit={handleSubmit}>
          <div className="profile-edit-dialog__row">
            <label className="profile-edit-dialog__field">
              <span>Фамилия</span>
              <input type="text" value={lastName} onChange={event => setLastName(event.target.value)} placeholder="Анучин" />
            </label>
            <label className="profile-edit-dialog__field">
              <span>Имя</span>
              <input type="text" value={firstName} onChange={event => setFirstName(event.target.value)} placeholder="Александр" />
            </label>
          </div>
          <label className="profile-edit-dialog__field">
            <span>Отчество</span>
            <input type="text" value={middleName} onChange={event => setMiddleName(event.target.value)} placeholder="Михайлович" />
          </label>
          <label className="profile-edit-dialog__field">
            <span>Email</span>
            <input type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="name@example.com" />
          </label>
          <label className="profile-edit-dialog__field">
            <span>Телефон</span>
            <input
              type="tel"
              value={phone}
              onChange={event => setPhone(formatPhoneInput(event.target.value, phone))}
              placeholder="+7 (999) 123-45-67"
            />
          </label>
          <fieldset className="profile-edit-dialog__fieldset">
            <legend>Уровень программы</legend>
            {levelOptions.map(option => (
              <label key={option.value} className={`profile-edit-dialog__radio ${experienceLevel === option.value ? 'is-active' : ''}`}>
                <input
                  type="radio"
                  name="experience_level"
                  value={option.value}
                  checked={experienceLevel === option.value}
                  onChange={() => setExperienceLevel(option.value)}
                />
                <span className="profile-edit-dialog__radio-label">{option.label}</span>
                <span className="profile-edit-dialog__radio-description">{option.description}</span>
              </label>
            ))}
          </fieldset>
          <div className="profile-edit-dialog__row">
            <label className="profile-edit-dialog__field">
              <span>Новый пароль</span>
              <input type="password" value={password} onChange={event => setPassword(event.target.value)} placeholder="Оставьте пустым, чтобы не менять" />
            </label>
            <label className="profile-edit-dialog__field">
              <span>Повторите пароль</span>
              <input type="password" value={passwordConfirm} onChange={event => setPasswordConfirm(event.target.value)} placeholder="Повторите пароль" />
            </label>
          </div>
          <div className="profile-edit-dialog__actions">
            <button type="button" className="profile-edit-dialog__secondary" onClick={onClose} disabled={submitting}>
              Отмена
            </button>
            <button type="submit" className="profile-edit-dialog__primary" disabled={submitting}>
              {submitting ? 'Сохраняем…' : 'Сохранить изменения'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    modalRoot
  )
}