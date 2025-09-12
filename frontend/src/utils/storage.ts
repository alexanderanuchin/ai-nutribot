const ACCESS_KEY = 'nutribot_access'
const REFRESH_KEY = 'nutribot_refresh'

export const tokenStore = {
  get access(){ return localStorage.getItem(ACCESS_KEY) || '' },
  set access(v: string){ if(v){ localStorage.setItem(ACCESS_KEY, v) } else { localStorage.removeItem(ACCESS_KEY) } },
  get refresh(){ return localStorage.getItem(REFRESH_KEY) || '' },
  set refresh(v: string){ if(v){ localStorage.setItem(REFRESH_KEY, v) } else { localStorage.removeItem(REFRESH_KEY) } },
  clear(){ localStorage.removeItem(ACCESS_KEY); localStorage.removeItem(REFRESH_KEY) }
}
