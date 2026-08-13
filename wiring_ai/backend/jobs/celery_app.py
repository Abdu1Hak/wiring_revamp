# celery_app.py
# -------------
# Celery distributed task queue configuration for Wiring AI.
# Offloads compute-heavy asynchronous operations (datasheet PDF ingestion, OCR, LLM extraction, vector indexing)
# to background worker processes using Redis as broker and result backend.

import os
from celery import Celery
from dotenv import load_dotenv

# Load environment configuration
db_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(db_dir, "db", ".env"))
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://:redis_password@localhost:6379/0")

# ==============================================================================
# CELERY TASK QUEUE INITIALIZATION (celery_app.py)
# ==============================================================================
# WHAT IS CELERY?
# Celery is a task queue framework. It allows FastAPI to offload heavy or slow
# functions to a separate background worker process (Terminal 2), keeping FastAPI
# (Terminal 1) lightning fast.
#
# WHAT ARE THE TWO ROLES OF REDIS HERE?
# 1. BROKER (`broker=REDIS_URL`):
#    The "Message Queue Inbox". When FastAPI calls `.delay()`, it drops a message 
#    into Redis saying: "Hey worker, please run this task!".
# 2. BACKEND (`backend=REDIS_URL`):
#    The "Task Result Storage". When the worker finishes running the task, it 
#    writes the final return value and status ("SUCCESS", "FAILURE") into Redis 
#    so FastAPI and the frontend can read the result.
# ==============================================================================

# Initialize Celery app instance
celery_app = Celery(
    "wiring_ai",
    broker=REDIS_URL, # redis used as a queue broker (fastapi drops task message here)
    backend=REDIS_URL, # redis used as a result backend (worker finished output here)
    include=["jobs.tasks"],  # Tells Celery to load background functions from tasks.py
)

# Celery Configuration Settings
celery_app.conf.update(
    task_serializer="json",       # Convert task arguments into JSON text for Redis
    result_serializer="json",     # Convert return values into JSON text for Redis
    accept_content=["json"],       # Only accept secure JSON payloads
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,          # Retain finished task results in Redis for 1 hour
    task_track_started=True,      # Track when a task transitions from PENDING -> STARTED
    task_time_limit=600,          # Hard timeout: Kill tasks exceeding 10 minutes
    task_soft_time_limit=540,      # Soft timeout: Warn tasks exceeding 9 minutes
    worker_prefetch_multiplier=1, # Fetch 1 task at a time per worker for fair load distribution
)

if __name__ == "__main__":
    celery_app.start()
