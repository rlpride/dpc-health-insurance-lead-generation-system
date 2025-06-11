"""Worker for synchronizing data with Pipedrive CRM."""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.pipedrive import PipedriveIntegrationService
from config.settings import get_settings
from models.base import Base

logger = logging.getLogger(__name__)


class PipedriveSyncWorker:
    """Worker for syncing data to Pipedrive CRM."""
    
    def __init__(self):
        """Initialize the Pipedrive sync worker."""
        self.settings = get_settings()
        
        # Database setup
        self.engine = create_engine(
            str(self.settings.database_url),
            pool_size=self.settings.database_pool_size,
            max_overflow=self.settings.database_max_overflow,
            echo=self.settings.debug
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self.is_running = False
        self.last_sync_time = None
        
    async def start(self):
        """Start the sync worker."""
        self.is_running = True
        logger.info("Starting Pipedrive sync worker...")
        
        try:
            while self.is_running:
                await self.sync_cycle()
                
                # Wait before next cycle (default 30 minutes)
                await asyncio.sleep(1800)  # 30 minutes
                
        except Exception as e:
            logger.error(f"Error in sync worker: {e}")
            raise
        finally:
            logger.info("Pipedrive sync worker stopped")
    
    def stop(self):
        """Stop the sync worker."""
        self.is_running = False
        logger.info("Stopping Pipedrive sync worker...")
    
    async def sync_cycle(self):
        """Perform one sync cycle."""
        start_time = datetime.utcnow()
        logger.info("Starting Pipedrive sync cycle...")
        
        db = self.SessionLocal()
        
        try:
            async with PipedriveIntegrationService(db) as service:
                # Sync pending records
                stats = await service.sync_pending_records(limit=100)
                
                # Log results
                logger.info(f"Sync cycle completed in {(datetime.utcnow() - start_time).total_seconds():.2f}s")
                logger.info(f"Stats: {stats}")
                
                self.last_sync_time = start_time
                
        except Exception as e:
            logger.error(f"Error during sync cycle: {e}")
            raise
        finally:
            db.close()
    
    async def sync_high_priority_leads(self):
        """Sync only high-priority leads (score >= 80)."""
        logger.info("Syncing high-priority leads...")
        
        db = self.SessionLocal()
        
        try:
            async with PipedriveIntegrationService(db) as service:
                from models.company import Company
                
                # Get high-scoring companies that need sync
                high_score_companies = (
                    db.query(Company)
                    .filter(
                        Company.lead_score >= self.settings.high_score_threshold,
                        Company.crm_sync_status == 'pending'
                    )
                    .limit(50)
                    .all()
                )
                
                synced_count = 0
                deals_created = 0
                
                for company in high_score_companies:
                    try:
                        # Sync company
                        success = await service.sync_company(company)
                        if success:
                            synced_count += 1
                            
                            # Create deal
                            deal_success = await service.create_deal_for_high_score_lead(company)
                            if deal_success:
                                deals_created += 1
                    
                    except Exception as e:
                        logger.error(f"Error syncing high-priority company {company.name}: {e}")
                        continue
                
                logger.info(f"High-priority sync completed: {synced_count} companies, {deals_created} deals")
                
        except Exception as e:
            logger.error(f"Error during high-priority sync: {e}")
            raise
        finally:
            db.close()
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get current worker status."""
        return {
            'is_running': self.is_running,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'settings': {
                'high_score_threshold': self.settings.high_score_threshold,
                'pipedrive_domain': self.settings.pipedrive_domain,
            }
        }


async def run_pipedrive_sync_worker():
    """Main function to run the Pipedrive sync worker."""
    worker = PipedriveSyncWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        worker.stop()
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the worker
    asyncio.run(run_pipedrive_sync_worker())