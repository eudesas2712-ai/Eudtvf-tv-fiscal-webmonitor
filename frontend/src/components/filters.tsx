"use client";

import { useState } from "react";

export default function Filters({ onSubmit }: { onSubmit: (q: string) => void }) {
  const [q, setQ] = useState("");
  return (
    <div className="card" style={{marginBottom:12}}>
      <div className="h2">Filtro rápido</div>
      <div className="grid" style={{gridTemplateColumns:"1fr 140px"}}>
        <input className="input" value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Buscar (ex: Cabedelo, Unimed, Walber...)" />
        <button className="btn" onClick={()=>onSubmit(q)}>Buscar</button>
      </div>
    </div>
  );
}