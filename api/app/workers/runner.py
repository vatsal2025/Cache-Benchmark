"""
RQ worker entrypoint — processes all job queues.
"""
import logging
import sys
from rq import Worker
from app.core.redis import get_redis

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    conn = get_redis()
    worker = Worker(["attack", "experiment", "export", "default"], connection=conn)
    logger.info("Worker started, listening on queues: attack, experiment, export, default")
    worker.work(with_scheduler=True)
