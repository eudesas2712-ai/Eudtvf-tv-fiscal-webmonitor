from sqlalchemy.orm import Session
from app.db.models import Project, Source, WatchTerm, Rule

def bootstrap_project(db: Session):
    # Cria 1 projeto com suas fontes/termos/regras.
    existing = db.query(Project).filter(Project.name == "Tv Fiscal WebMonitor").first()
    if existing:
        return existing

    p = Project(
        name="Tv Fiscal WebMonitor",
        client_name="TV Fiscal",
        active=True,
    )
    db.add(p)
    db.flush()

    # URLs: ajuste se quiser (RSS pode variar por portal; se vazio, usamos base_url como lista).
    sources = [
        Source(project_id=p.id, name="Portal Correio", base_url="https://portalcorreio.com.br/", rss_url=None, enabled=True, interval_minutes=15),
        Source(project_id=p.id, name="PB Agora", base_url="https://www.pbagora.com.br/", rss_url=None, enabled=True, interval_minutes=15),
        Source(project_id=p.id, name="Polêmica Paraíba", base_url="https://www.polemicaparaiba.com.br/", rss_url=None, enabled=True, interval_minutes=15),
    ]
    db.add_all(sources)

    # Termos (com pequenas aliases úteis)
    term_list = [
        ("Walber Virgulino", {"aliases":["Walber", "Virgulino"]}, 5),
        ("Prefeitura de Cabedelo", {"aliases":["Prefeitura Cabedelo","PM Cabedelo"]}, 5),
        ("Eleições Cabedelo", {"aliases":["eleicao cabedelo","eleições em cabedelo"]}, 4),
        ("Governo da Paraíba", {"aliases":["Governo da Paraiba","Gov. da Paraíba","Governo PB"]}, 4),
        ("Intermares", {"aliases":[]}, 3),
        ("poço", {"aliases":["poco"]}, 2),
        ("camboinha", {"aliases":["Camboinha"]}, 3),
        ("jacaré", {"aliases":["jacare"]}, 2),
        ("porto de cabedelo", {"aliases":["Porto de Cabedelo","porto cabedelo"]}, 4),
        ("Unimed", {"aliases":[]}, 3),
    ]
    for term, aliases, pr in term_list:
        db.add(WatchTerm(project_id=p.id, term=term, aliases={"aliases": aliases.get("aliases", [])}, match_mode="phrase", priority=pr))

    # Regras (inclui amarração para ambíguos)
    rules = [
        Rule(
            project_id=p.id,
            name="Cabedelo - Institucional/Eleitoral",
            severity="high",
            enabled=True,
            query_dsl={"or":[
                {"phrase":"prefeitura de cabedelo"},
                {"phrase":"eleições cabedelo"},
                {"phrase":"porto de cabedelo"},
            ]}
        ),
        Rule(
            project_id=p.id,
            name="Walber Virgulino",
            severity="high",
            enabled=True,
            query_dsl={"or":[
                {"phrase":"walber virguilino"},
                {"phrase":"walber virgulino"},
                {"near":{"a":"walber","b":"virgulino","w":3}}
            ]}
        ),
        Rule(
            project_id=p.id,
            name="Governo da Paraíba",
            severity="med",
            enabled=True,
            query_dsl={"or":[
                {"phrase":"governo da paraíba"},
                {"phrase":"governo da paraiba"},
                {"phrase":"governo pb"}
            ]}
        ),
        Rule(
            project_id=p.id,
            name="Termos ambíguos (amarrados em Cabedelo)",
            severity="med",
            enabled=True,
            query_dsl={"and":[
                {"or":[{"phrase":"poço"},{"phrase":"poco"},{"phrase":"jacaré"},{"phrase":"jacare"}]},
                {"or":[{"phrase":"cabedelo"},{"phrase":"intermares"},{"phrase":"cամբoinha"},{"phrase":"camboinha"},{"phrase":"porto de cabedelo"}]}
            ]}
        ),
        Rule(
            project_id=p.id,
            name="Unimed contextualizada",
            severity="med",
            enabled=True,
            query_dsl={"and":[
                {"phrase":"unimed"},
                {"or":[{"phrase":"paraíba"},{"phrase":"paraiba"},{"phrase":"joão pessoa"},{"phrase":"cabedelo"}]}
            ]}
        ),
    ]
    db.add_all(rules)

    db.commit()
    db.refresh(p)
    return p