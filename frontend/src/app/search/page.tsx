"use client";

import Nav from "../../components/Nav";
import Filters from "../../components/Filters";
import DataTable from "../../components/DataTable";
import { apiGet } from "../../lib/api";
import type { SearchResult } from "../../lib/types";
import { useEffect, useState } from "react";

async function getProjectId(): Promise<string | null> {
  const r = await fetch("http://localhost:8000/projects/", { cache: "no-store" });
  if (!r.ok) return null;
  const projects = await r.json();
  return projects?.[0]?.id || null;
}

export default function SearchPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState<number>(0);

  useEffect(() => {
    getProjectId().then(setProjectId);
  }, []);

  async function run(q: string) {
    if (!projectId) return;
    const res = await apiGet<SearchResult>(`/search?project_id=${projectId}&q=${encodeURIComponent(q)}&size=50&offset=0`);
    setItems(res.items);
    setTotal(res.total);
  }

  return (
    <>
      <Nav />
      {!projectId ? (
        <div className="card">Nenhum projeto. Faça bootstrap no Swagger: POST /projects/bootstrap</div>
      ) : (
        <>
          <Filters onSubmit={run} />
          <div className="card">
            <div className="h2">Resultados</div>
            <div className="small">Total: {total}</div>
          </div>
          <div className="card" style={{marginTop:12}}>
            <DataTable items={items} />
          </div>
        </>
      )}
    </>
  );
}