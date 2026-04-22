import Nav from "../../../components/Nav";
import { apiGet } from "../../../lib/api";
import type { ItemDetail } from "../../../lib/types";

export default async function ItemPage({ params }: { params: { id: string } }) {
  const detail = await apiGet<ItemDetail>(`/items/${params.id}`);

  if (!detail?.item) {
    return (
      <>
        <Nav />
        <div className="card">Item não encontrado.</div>
      </>
    );
  }

  return (
    <>
      <Nav />
      <div className="card">
        <div className="h2">{detail.item.title || "(sem título)"}</div>
        <div className="small">
          <a href={detail.item.url} target="_blank">Abrir URL</a>
          {" • "}
          {detail.evidence_html_url ? <a href={detail.evidence_html_url} target="_blank">Evidência HTML (MinIO)</a> : "sem evidência"}
        </div>
        <div style={{marginTop:12}} className="small">
          <b>Score:</b> {detail.item.score ?? 0}{" "}
          <b style={{marginLeft:10}}>Matches:</b> {JSON.stringify(detail.match || {})}
        </div>
      </div>

      <div className="card" style={{marginTop:12}}>
        <div className="h2">Conteúdo</div>
        <pre style={{whiteSpace:"pre-wrap", fontFamily:"inherit"}}>{detail.content_text || "(sem texto extraído)"}</pre>
      </div>
    </>
  );
}