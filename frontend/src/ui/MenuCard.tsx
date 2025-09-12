import React from 'react'
import type { PlanMeal } from '../types'

export default function MenuCard({ item }: { item: PlanMeal }){
  return (
    <div className="card" style={{marginTop:8}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:8}}>
        <div>
          <b>{item.title || `Позиция #${item.item_id}`}</b>
          <div className="small">Приём: {item.time_hint}</div>
        </div>
        <div className="badge">x{item.qty}</div>
      </div>
    </div>
  )
}
