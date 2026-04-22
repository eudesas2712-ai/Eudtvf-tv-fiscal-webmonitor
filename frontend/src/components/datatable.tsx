import Badge from "./Badge";
import type { SearchItem } from "../lib/types";

export default function DataTable({ items }: { items: SearchItem[] }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th style={{width:"60%"}}>Título / URL</th>
          <th>Score</th>
          <th>Sev</th>
          <th>Termos</th>
        </tr>
      </thead>
      <tbody>
        {items.map((it) => (
          <tr key={it.id}>
            <td>
              <div style={{fontWeight:600, marginBottom:6}}>
                <a href={`/items/${it.id}`}>{it.title || "(sem título)"}</a>
              </div>
              <div className="small"><a href={it.url} target="_blank">{it.url}</a></div>
            </td>
            <td>{(it.score ?? 0).toFixed(1)}</td>
            <td><Badge label={it.severity || "low"} /></td>
            <td className="small">{(it.matched_terms?.terms || []).slice(0,6).join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}