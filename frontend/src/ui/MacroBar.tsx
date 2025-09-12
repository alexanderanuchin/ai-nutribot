import React, { useEffect, useRef } from 'react'
import type { Targets } from '../types'

function Bar({label, value, max}:{label:string, value:number, max:number}){
  const ref = useRef<HTMLSpanElement>(null)
  const pct = Math.min(100, Math.round((value/max)*100))
  useEffect(()=>{ if(ref.current) ref.current.style.width = pct + '%' }, [pct])
  return (
    <div style={{margin:'8px 0'}}>
      <div className="small" style={{display:'flex',justifyContent:'space-between'}}>
        <span>{label}</span><span>{value}</span>
      </div>
      <div className="progress"><span ref={ref}></span></div>
    </div>
  )
}

export default function MacroBar({ targets }: {targets: Targets}){
  return (
    <div>
      <div className="badge">Цель: {targets.calories} ккал</div>
      <Bar label="Белки (г)" value={targets.protein_g} max={targets.protein_g}/>
      <Bar label="Жиры (г)"  value={targets.fat_g} max={targets.fat_g}/>
      <Bar label="Углеводы (г)" value={targets.carbs_g} max={targets.carbs_g}/>
    </div>
  )
}
