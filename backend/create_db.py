import asyncio
from app.core.database import get_engine
from app.db.base import Base
from app.db import models, threat_memory_models
async def main():
    async with get_engine().begin() as c:
        await c.run_sync(Base.metadata.create_all)
    print("Database ready.")
asyncio.run(main())
