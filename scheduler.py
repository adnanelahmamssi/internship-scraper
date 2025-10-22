from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from database import get_db_session
from models import Offer, ScrapingStat
from scraper.indeed_scraper import scrape_indeed, extract_country_from_location, parse_date_posted
from sqlalchemy.exc import IntegrityError
import logging
import time
import os
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def insert_new_offers(offers):
    db = get_db_session()
    inserted = 0
    try:
        for o in offers:
            try:
                # Extract country and parse date
                location = o.get("location", "")
                date_posted = o.get("date_posted", "")
                country = extract_country_from_location(location)
                date_parsed = parse_date_posted(date_posted)
                
                offer = Offer(
                    title=o.get("title", ""),
                    company=o.get("company", ""),
                    location=location,
                    country=country,
                    date_posted=date_posted,
                    date_posted_parsed=date_parsed,
                    link=o.get("link", ""),
                )
                db.add(offer)
                db.commit()
                inserted += 1
            except IntegrityError:
                db.rollback()
                # Duplicate link; skip
            except Exception as e:
                logger.error(f"Error inserting offer: {e}")
                db.rollback()
        logger.info(f"Inserted {inserted} new offers into the database")
        return inserted
    except Exception as e:
        logger.error(f"Error in insert_new_offers: {e}")
        logger.error(traceback.format_exc())
        return 0
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Error closing database session: {e}")


def run_scrape_job(max_pages: int = 1, country: str = "Maroc") -> int:
    # Reduce pages in cloud environments
    if os.environ.get('RENDER'):
        max_pages = min(max_pages, 1)  # Maximum 1 page in cloud environments
        print(f"Cloud environment detected, limiting to {max_pages} pages")
    
    start_time = time.time()
    logger.info(f"Starting scraping job for {country} with max_pages={max_pages}")
    
    offers_found = 0
    inserted = 0
    
    try:
        # Scrape the offers
        offers = scrape_indeed(max_pages=max_pages, country=country)
        offers_found = len(offers)
        
        # Insert new offers
        inserted = insert_new_offers(offers)
    except Exception as e:
        logger.error(f"Scraping failed for {country}: {e}")
        logger.error(traceback.format_exc())
        offers_found = 0
        inserted = 0
        # Continue to record stats even if scraping failed
    
    # Record scraping statistics
    end_time = time.time()
    duration = int(end_time - start_time)
    
    db = get_db_session()
    try:
        stat = ScrapingStat(
            country=country,
            offers_found=offers_found,
            offers_inserted=inserted,
            execution_time=datetime.now(),
            duration_seconds=duration
        )
        db.add(stat)
        db.commit()
        logger.info(f"Scraping stats recorded for {country}: {offers_found} found, {inserted} inserted in {duration} seconds")
    except Exception as e:
        logger.error(f"Failed to record scraping stats for {country}: {e}")
        logger.error(traceback.format_exc())
        db.rollback()
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Error closing database session: {e}")
    
    logger.info(f"Scraping completed for {country}. Found {offers_found} offers, inserted {inserted}")
    return inserted


def get_next_run_times(scheduler):
    """Get the next run times for all scraping jobs"""
    next_runs = {}
    job_ids = [
        "indeed_scrape_job_maroc",
        "indeed_scrape_job_france",
        "indeed_scrape_job_canada",
        "indeed_scrape_job_belgique",
        "indeed_scrape_job_suisse"
    ]
    
    for job_id in job_ids:
        try:
            job = scheduler.get_job(job_id)
            if job:
                next_runs[job_id] = job.next_run_time
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
    
    return next_runs


def create_scheduler() -> BackgroundScheduler:
    logger.info("Creating scheduler...")
    scheduler = BackgroundScheduler()
    
    # Every 1 hour for Morocco
    scheduler.add_job(
        func=lambda: run_scrape_job(max_pages=1, country="Maroc"),
        trigger="interval",
        minutes=15,
        id="indeed_scrape_job_maroc",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    
    # Every 1 hour for France
    scheduler.add_job(
        func=lambda: run_scrape_job(max_pages=1, country="France"),
        trigger="interval",
        minutes=15,
        id="indeed_scrape_job_france",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    
    # Every 1 hour for Canada
    scheduler.add_job(
        func=lambda: run_scrape_job(max_pages=1, country="Canada"),
        trigger="interval",
        minutes=15,
        id="indeed_scrape_job_canada",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    
    # Every 1 hour for Belgium
    scheduler.add_job(
        func=lambda: run_scrape_job(max_pages=1, country="Belgique"),
        trigger="interval",
        minutes=15,
        id="indeed_scrape_job_belgique",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    
    # Every 1 hour for Switzerland
    scheduler.add_job(
        func=lambda: run_scrape_job(max_pages=1, country="Suisse"),
        trigger="interval",
        minutes=15,
        id="indeed_scrape_job_suisse",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    
    logger.info("Scheduler created with 5 jobs (15 minutes interval)")
    return scheduler