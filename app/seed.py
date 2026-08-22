import os
import json
import logging
from app.db.database import Base, engine, SessionLocal
from app.models.models import ContextSection, BacklogItemModel
from app.services.context_service import ContextService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


def seed_database():
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    data_dir = os.getenv("DATA_DIR", "./data")

    # 1. Index Product Brief
    brief_path = os.path.join(data_dir, "product_brief.md")
    if os.path.exists(brief_path):
        context_svc = ContextService(db)
        count = context_svc.index_markdown(brief_path, doc_name="product_brief.md")
        logger.info(f"Indexed {count} sections from product_brief.md")
    else:
        logger.warning(f"Product brief not found at {brief_path}")

    # 2. Seed Backlog Items
    backlog_path = os.path.join(data_dir, "backlog.json")
    if os.path.exists(backlog_path):
        with open(backlog_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        db.query(BacklogItemModel).delete()
        db.commit()

        for item in items:
            db_item = BacklogItemModel(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                acceptance_criteria=item.get("acceptance_criteria", ""),
                citations=json.dumps(item.get("citations", [])),
                status=item.get("status", "NOT_READY")
            )
            db.add(db_item)

        db.commit()
        logger.info(f"Seeded {len(items)} backlog items into database.")

    db.close()
    logger.info("Database seeding complete!")


if __name__ == "__main__":
    seed_database()
