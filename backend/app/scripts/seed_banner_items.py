import random
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import BannerItem
from app.db.session import SessionLocal


DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb"


def seed_banner_items(
    db: Optional[Session] = None,
    project_id: str = DEFAULT_PROJECT_ID,
    quantity: int = 250,
    replace: bool = False,
) -> None:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    assert db is not None

    project_uuid = uuid.UUID(project_id)

    advertisers = [
        "TIM",
        "Vivo",
        "Claro",
        "Banco do Brasil",
        "Caixa",
        "Prefeitura de João Pessoa",
        "Governo da Paraíba",
        "Unimed",
        "Magalu",
        "Casas Bahia",
    ]

    portals = [
        "www.polemicaparaiba.com.br",
        "www.portalcorreio.com.br",
        "www.clickpb.com.br",
        "www.wscom.com.br",
        "www.jornaldaparaiba.com.br",
    ]

    if replace:
        db.query(BannerItem).filter(BannerItem.project_id == project_uuid).delete()

    for i in range(quantity):
        advertiser = random.choice(advertisers)
        portal = random.choice(portals)

        item = BannerItem(
            project_id=project_uuid,
            page_url=f"https://{portal}/noticia/{i}",
            image_url=f"https://{portal}/banner/{i}.jpg",
            alt_text=advertiser,
            width=random.choice([300, 728, 160]),
            height=random.choice([250, 90, 600]),
            normalized_width=300,
            normalized_height=250,
            estimated_value=random.randint(50, 500),
            pos_x=random.randint(0, 1000),
            pos_y=random.randint(0, 2000),
            source_name=portal,
            advertiser_name=advertiser,
            classification="Publicidade",
            classification_score=random.randint(70, 100),
            classification_reason="Simulado",
            ocr_text=advertiser,
            created_at=datetime.utcnow(),
        )
        db.add(item)

    db.commit()

    if own_session:
        db.close()


if __name__ == "__main__":
    seed_banner_items()
    print("✅ 250 banners inseridos com sucesso")