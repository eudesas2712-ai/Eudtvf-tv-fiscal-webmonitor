export default function Nav() {
  return (
    <div className="topbar">
      <div>
        <div className="h1">TV Fiscal WebMonitor</div>
        <div className="small">Monitoramento de portais/blogs (MVP) • Inbox • Busca • Evidências</div>
      </div>
      <div className="nav">
        <a className="btn" href="/">Dashboard</a>
        <a className="btn" href="/inbox">Inbox</a>
        <a className="btn" href="/search">Search</a>
      </div>
    </div>
  );
}