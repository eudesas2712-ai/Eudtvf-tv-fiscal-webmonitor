import Nav from "../../components/Nav";
import DataTable from "../../components/DataTable";
import { apiGet } from "../../lib/api";
import type { SearchResult } from "../../lib/types";

async function getProjectId(): Promise<string | null> {
  const projects = await apiGet<any[]>("/projects/");
  return projects?.[0]?.id || null;
}

export default async function Inbox() {
  const projectId = await getProjectId();
  if (!projectId) {
    return (
      <>
        <Nav />
        <div className="card">Nenhum projeto. Faça bootstrap no Swagger: POST /projects/bootstrap</div>
      </>
    );
  }

  const res = await apiGet<SearchResult>(`/search?project_id=${projectId}&size=25&offset=0`);
  return (
    <>
      <Nav />
      <div className="card">
        <div className="h2">Inbox (últimos itens)</div>
        <div className="small">Project: {projectId}</div>
      </div>
      <div className="card" style={{marginTop:12}}>
        <DataTable items={res.items} />
      </div>
    </>
  );
}