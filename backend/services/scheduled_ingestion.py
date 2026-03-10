"""
Scheduled Ingestion Service

Manages background jobs for periodic data syncing from source databases to vector database.
Implements polling-based ETL with configurable intervals per table.
"""

import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from backend.services.ingestion_pipeline import IngestionPipeline
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class ScheduledIngestionService:
    """Service for managing scheduled data ingestion jobs."""

    def __init__(self):
        """Initialize the scheduled ingestion service."""
        self.pipeline = IngestionPipeline()
        self.jobs = {}  # Map of job_id -> job_config
        self.scheduler_thread = None
        self.is_running = False
        self.job_locks = {}  # Prevent concurrent runs of same job
        logger.info("✓ ScheduledIngestionService initialized")

    def start_ingestion_job(self, database_setting: Dict[str, Any]) -> str:
        """
        Start a new ingestion job for a database.
        
        Args:
            database_setting: Database configuration with selected_tables
            
        Returns:
            Job ID
        """
        try:
            job_id = database_setting.get('id')
            if not job_id:
                raise ValueError("Database setting must have an ID")
            
            db_name = database_setting.get('name')
            logger.info(f"→ Starting ingestion job for database: {db_name}")
            
            # Store job configuration
            self.jobs[job_id] = {
                'database_setting': database_setting,
                'created_at': datetime.utcnow(),
                'last_run': None,
                'next_run': datetime.utcnow(),
                'success_count': 0,
                'error_count': 0,
                'last_error': None
            }
            
            self.job_locks[job_id] = threading.Lock()
            
            # Schedule the job
            self._schedule_job(job_id, database_setting)
            
            # Start scheduler if not running
            if not self.is_running:
                self._start_scheduler()
            
            logger.info(f"✓ Ingestion job started: {job_id} for {db_name}")
            return job_id
            
        except Exception as e:
            logger.error(f"✗ Error starting ingestion job: {str(e)}")
            raise

    def _schedule_job(self, job_id: str, database_setting: Dict[str, Any]):
        """Schedule periodic ingestion for a database."""
        try:
            selected_tables = database_setting.get('selected_tables', {})
            
            # Find minimum sync interval across all enabled tables
            min_interval = 60  # Default 1 hour
            for table_config in selected_tables.values():
                if table_config.get('enabled'):
                    interval = table_config.get('sync_interval', 60)
                    min_interval = min(min_interval, interval)
            
            # Schedule with the minimum interval
            schedule.every(min_interval).minutes.do(
                self._run_ingestion_job,
                job_id
            ).tag(job_id)
            
            logger.info(f"→ Scheduled ingestion for {job_id} every {min_interval} minutes")
            
        except Exception as e:
            logger.error(f"✗ Error scheduling job: {str(e)}")

    def _run_ingestion_job(self, job_id: str):
        """Execute a scheduled ingestion job."""
        try:
            # Prevent concurrent executions
            if not self.job_locks[job_id].acquire(blocking=False):
                logger.warning(f"⊗ Ingestion job {job_id} already running, skipping")
                return
            
            try:
                if job_id not in self.jobs:
                    logger.warning(f"✗ Job {job_id} not found")
                    return
                
                job_config = self.jobs[job_id]
                database_setting = job_config['database_setting']
                db_name = database_setting.get('name')
                
                logger.info(f"→ Running ingestion job: {job_id} ({db_name})")
                
                # Run the ingestion pipeline
                result = self.pipeline.ingest_database(database_setting)
                
                # Update job metrics
                job_config['last_run'] = datetime.utcnow()
                if result['status'] == 'success':
                    job_config['success_count'] += 1
                    job_config['last_error'] = None
                    logger.info(
                        f"✓ Ingestion successful for {db_name}: "
                        f"{result['tables_ingested']} tables, "
                        f"{result['total_records']} records, "
                        f"{result['total_chunks']} chunks"
                    )
                else:
                    job_config['error_count'] += 1
                    job_config['last_error'] = result.get('error')
                    logger.error(f"✗ Ingestion failed for {db_name}: {result.get('error')}")
                
                # Calculate next run
                selected_tables = database_setting.get('selected_tables', {})
                min_interval = 60
                for table_config in selected_tables.values():
                    if table_config.get('enabled'):
                        interval = table_config.get('sync_interval', 60)
                        min_interval = min(min_interval, interval)
                
                job_config['next_run'] = datetime.utcnow() + timedelta(minutes=min_interval)
                
            finally:
                self.job_locks[job_id].release()
                
        except Exception as e:
            logger.error(f"✗ Error running ingestion job: {str(e)}")
            if job_id in self.jobs:
                self.jobs[job_id]['error_count'] += 1
                self.jobs[job_id]['last_error'] = str(e)

    def _start_scheduler(self):
        """Start the background scheduler thread."""
        try:
            if self.is_running:
                return
            
            self.is_running = True
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True
            )
            self.scheduler_thread.start()
            logger.info("✓ Scheduler thread started")
            
        except Exception as e:
            logger.error(f"✗ Error starting scheduler: {str(e)}")

    def _scheduler_loop(self):
        """Main scheduler loop running in background thread."""
        try:
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"✗ Error in scheduler loop: {str(e)}")
                    time.sleep(5)
        except Exception as e:
            logger.error(f"✗ Scheduler thread error: {str(e)}")
        finally:
            self.is_running = False

    def stop_ingestion_job(self, job_id: str) -> bool:
        """
        Stop an ingestion job.
        
        Args:
            job_id: ID of the job to stop
            
        Returns:
            True if successful
        """
        try:
            # Remove scheduled tasks with this job_id
            schedule.clear(job_id)
            
            # Remove job configuration
            if job_id in self.jobs:
                del self.jobs[job_id]
            
            if job_id in self.job_locks:
                del self.job_locks[job_id]
            
            logger.info(f"✓ Stopped ingestion job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error stopping ingestion job: {str(e)}")
            return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an ingestion job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            Job status information
        """
        try:
            if job_id not in self.jobs:
                return None
            
            job_config = self.jobs[job_id]
            return {
                'job_id': job_id,
                'database': job_config['database_setting'].get('name'),
                'created_at': job_config['created_at'].isoformat(),
                'last_run': job_config['last_run'].isoformat() if job_config['last_run'] else None,
                'next_run': job_config['next_run'].isoformat() if job_config['next_run'] else None,
                'success_count': job_config['success_count'],
                'error_count': job_config['error_count'],
                'last_error': job_config['last_error'],
                'is_running': self.is_running
            }
            
        except Exception as e:
            logger.error(f"✗ Error getting job status: {str(e)}")
            return None

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get status of all active jobs."""
        try:
            return [
                self.get_job_status(job_id)
                for job_id in self.jobs.keys()
                if self.get_job_status(job_id)
            ]
        except Exception as e:
            logger.error(f"✗ Error getting all jobs: {str(e)}")
            return []

    def pause_scheduler(self):
        """Pause the scheduler (jobs won't run but remain registered)."""
        self.is_running = False
        logger.info("✓ Scheduler paused")

    def resume_scheduler(self):
        """Resume the scheduler."""
        if not self.is_running:
            self._start_scheduler()
        logger.info("✓ Scheduler resumed")

    def shutdown(self):
        """Shutdown the ingestion service."""
        try:
            self.is_running = False
            schedule.clear()
            self.jobs.clear()
            logger.info("✓ ScheduledIngestionService shut down")
        except Exception as e:
            logger.error(f"✗ Error shutting down service: {str(e)}")


# Global instance
_ingestion_service = None


def get_ingestion_service() -> ScheduledIngestionService:
    """Get the global ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = ScheduledIngestionService()
    return _ingestion_service
