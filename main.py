import asyncio
import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import init_db
import api as api_module

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup va shutdown"""
    # Startup
    init_db()
    logger.info("✅ FastAPI server started")
    
    # Bot va Schedulerni parallel ishga tushirish
    from bot import run_bot
    bot_task = asyncio.create_task(run_bot())
    
    yield
    
    # Shutdown
    bot_task.cancel()
    logger.info("Server stopped")


app = FastAPI(
    title="TSUE Study Assistant API",
    version="4.0.0",
    lifespan=lifespan
)

# API routerlarini ulash
app.include_router(api_module.router, prefix="/api")

# Static fayllarni ulash (WebApp)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    logger.info(f"Starting server on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
