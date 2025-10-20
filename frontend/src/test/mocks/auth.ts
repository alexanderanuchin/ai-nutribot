import type { AuthContextValue, AuthUser } from '../../providers/AuthProvider'

export function createMockAuthUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 101,
    fullName: 'Test User',
    email: 'test.user@example.com',
    avatarUrl: undefined,
    avatarState: {
      kind: 'initials',
      value: 'TU',
      color: '#6c5ce7',
    },
    avatarImageSrc: null,
    role: 'legend',
    locale: 'ru',
    mode: 'Легенда',
    featureFlags: {
      aiAssistant: true,
      aiCurator: true,
      marketplace: true,
      training: true,
      recovery: true,
      gadgets: true,
      integrations: true,
      riskForecast: true,
      documents: true,
      nutritionAnalytics: true,
      mealConstructor: true,
      ...(overrides.featureFlags ?? {}),
    },
    isStaff: true,
    ...overrides,
  }
}

export function createMockAuthContextValue(
  overrides: Partial<AuthContextValue & { user: Partial<AuthUser> }> = {},
): AuthContextValue {
  const userOverrides = overrides.user ?? {}
  const user = createMockAuthUser(userOverrides)

  return {
    ready: true,
    bootstrapping: false,
    authReady: true,
    refreshing: false,
    authenticated: true,
    logout: () => {},
    user,
    profile: undefined,
    ...Object.fromEntries(
      Object.entries(overrides).filter(([key]) => key !== 'user'),
    ),
  }
}