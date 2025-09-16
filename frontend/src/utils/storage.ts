const ACCESS_KEY = 'nutribot_access'
const REFRESH_KEY = 'nutribot_refresh'


export const AUTH_CHANGE_EVENT = 'nutribot:auth-change'

function emitAuthChange(){
  if(typeof window !== 'undefined'){
    window.dispatchEvent(new Event(AUTH_CHANGE_EVENT))
  }
}


export const tokenStore = {
  get access(){ return localStorage.getItem(ACCESS_KEY) || '' },
  set access(v: string){
    if(v){
      localStorage.setItem(ACCESS_KEY, v)
    } else {
      localStorage.removeItem(ACCESS_KEY)
    }
    emitAuthChange()
  },
  get refresh(){ return localStorage.getItem(REFRESH_KEY) || '' },
  set refresh(v: string){ if(v){ localStorage.setItem(REFRESH_KEY, v) } else { localStorage.removeItem(REFRESH_KEY) } },
  clear(){
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
    emitAuthChange()
  }
}
