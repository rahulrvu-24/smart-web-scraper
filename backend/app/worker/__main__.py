"""Run the worker on its own: `python -m app.worker` (instead of inside the API)."""

import asyncio
import logging

from app.core.config import get_settings
from app.worker.runner import run_worker

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run_worker(get_settings(), asyncio.Event()))
    except KeyboardInterrupt:
        pass
