import math
from datetime import datetime
from flask import Flask, request, render_template, jsonify, url_for, redirect, session, flash
from sqlalchemy import func
import traceback
import secrets
import os
import logging

from database import init_db, get_db_session
from models import Offer, User, ScrapingStat
from scheduler import create_scheduler, run_scrape_job, get_next_run_times
from scraper.indeed_scraper import scrape_indeed
from forms import LoginForm, RegistrationForm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    init_db()

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    def login_required(f):
        """Decorator to require login for routes"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Re-enable login requirement
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route("/login", methods=['GET', 'POST'])
    def login():
        # If user is already logged in, redirect to country selector
        if 'user_id' in session:
            return redirect(url_for('index'))
            
        form = LoginForm()
        if form.validate_on_submit():
            db = get_db_session()
            try:
                user = db.query(User).filter(User.email == form.email.data).first()
                if user and user.check_password(form.password.data):
                    session['user_id'] = user.id
                    session['user_email'] = user.email
                    # Mark that user has visited the country selector
                    session['visited_country_selector'] = True
                    return redirect(url_for('index'))
                else:
                    flash('Email ou mot de passe invalide.', 'error')
            finally:
                db.close()
        
        return render_template('login.html', form=form)

    @app.route("/register", methods=['GET', 'POST'])
    def register():
        # If user is already logged in, redirect to country selector
        if 'user_id' in session:
            return redirect(url_for('index'))
            
        form = RegistrationForm()
        if form.validate_on_submit():
            print("Form validated successfully")
            db = get_db_session()
            try:
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == form.email.data).first()
                if existing_user:
                    flash('Cette adresse email est déjà enregistrée.', 'error')
                    print("Email already exists")
                else:
                    user = User(
                        email=form.email.data,
                        first_name=form.first_name.data,
                        last_name=form.last_name.data
                    )
                    user.set_password(form.password.data)
                    db.add(user)
                    db.commit()
                    flash('Inscription réussie. Veuillez vous connecter.', 'success')
                    print("User registered successfully")
                    return redirect(url_for('login'))
            except Exception as e:
                db.rollback()
                flash('Échec de l\'inscription. Veuillez réessayer.', 'error')
                print(f"Registration error: {e}")
            finally:
                db.close()
        else:
            # Print form errors for debugging
            if form.errors:
                print("Form errors:", form.errors)
            else:
                print("Form not validated but no errors shown")
        
        return render_template('register.html', form=form)

    @app.route("/logout")
    def logout():
        session.clear()
        flash('Vous avez été déconnecté.', 'info')
        return redirect(url_for('login'))

    @app.route("/timer-info")
    @login_required
    def timer_info():
        """API endpoint to get timer information"""
        try:
            next_runs = get_next_run_times(scheduler)
            # Convert datetime objects to ISO format for JSON serialization
            next_runs_iso = {}
            for job_id, next_run_time in next_runs.items():
                next_runs_iso[job_id] = next_run_time.isoformat() if next_run_time else None
            
            return jsonify({
                "next_runs": next_runs_iso,
                "current_time": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/")
    @login_required
    def index():
        # Home page is a country selector
        countries = [
            {"code": "MA", "name": "Maroc", "flag": "🇲🇦"},
            {"code": "FR", "name": "France", "flag": "🇫🇷"},
            {"code": "CA", "name": "Canada", "flag": "🇨🇦"},
            {"code": "BE", "name": "Belgique", "flag": "🇧🇪"},
            {"code": "CH", "name": "Suisse", "flag": "🇨🇭"}
        ]
        # Mark that user has visited the country selector
        session['visited_country_selector'] = True
        
        # Get next run times for display
        next_runs = get_next_run_times(scheduler)
        
        return render_template("country_selector.html", countries=countries, next_runs=next_runs)

    @app.route("/offers")
    @login_required
    def all_offers():
        # Page that displays all internship offers
        db = get_db_session()
        try:
            page = max(int(request.args.get("page", 1)), 1)
            limit = 20
            title = request.args.get("title")
            company = request.args.get("company")
            city = request.args.get("city")
            country = request.args.get("country")
            date_filter = request.args.get("date_filter")

            q = db.query(Offer)
            if title:
                q = q.filter(Offer.title.ilike(f"%{title}%"))
            if company:
                q = q.filter(Offer.company.ilike(f"%{company}%"))
            if city:
                q = q.filter(Offer.location.ilike(f"%{city}%"))
            if country:
                q = q.filter(Offer.country.ilike(f"%{country}%"))
            
            # Filtrage par date - use date_posted_parsed if available, fallback to created_at
            if date_filter:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                if date_filter == "today":
                    # For today, prefer date_posted_parsed but fallback to created_at
                    q = q.filter(
                        (Offer.date_posted_parsed >= today) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(today, datetime.min.time())))
                    )
                elif date_filter == "week":
                    week_ago = today - timedelta(days=7)
                    q = q.filter(
                        (Offer.date_posted_parsed >= week_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(week_ago, datetime.min.time())))
                    )
                elif date_filter == "month":
                    month_ago = today - timedelta(days=30)
                    q = q.filter(
                        (Offer.date_posted_parsed >= month_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(month_ago, datetime.min.time())))
                    )
                elif date_filter == "3months":
                    three_months_ago = today - timedelta(days=90)
                    q = q.filter(
                        (Offer.date_posted_parsed >= three_months_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(three_months_ago, datetime.min.time())))
                    )

            total = q.count()
            total_pages = max(math.ceil(total / 20) if total else 1, 1)
            offers = (
                q.order_by(Offer.date_posted_parsed.desc().nulls_last(), Offer.created_at.desc())
                 .offset((page - 1) * limit)
                 .limit(limit)
                 .all()
            )
            
            # Récupérer les listes pour les dropdowns
            cities = [row[0] for row in db.query(Offer.location).distinct().all() if row[0]]
            countries = [row[0] for row in db.query(Offer.country).distinct().all() if row[0]]
            
            return render_template("index.html", 
                                 offers=offers, 
                                 page=page, 
                                 total_pages=total_pages,
                                 cities=sorted(cities),
                                 countries=sorted(countries),
                                 show_all_offers=True)  # Flag to indicate this is the all offers page
        except Exception as e:
            print(f"Error in all_offers: {e}")
            traceback.print_exc()
            return f"Error: {e}", 500
        finally:
            db.close()

    @app.route("/country/<country_name>")
    @login_required
    def country_offers(country_name):
        # Validate country name
        supported_countries = ["Maroc", "France", "Canada", "Belgique", "Suisse"]
        if country_name not in supported_countries:
            # Redirect to country selector if invalid country
            return redirect(url_for('index'))
        
        # Check if user has visited the country selector page
        if not session.get('visited_country_selector'):
            # Redirect to country selector if user hasn't visited it first
            return redirect(url_for('index'))
        
        # Mark that user has selected a country (so they can navigate between country pages)
        session['selected_country'] = country_name
        
        db = get_db_session()
        try:
            page = max(int(request.args.get("page", 1)), 1)
            limit = 20
            title = request.args.get("title")
            company = request.args.get("company")
            city = request.args.get("city")
            date_filter = request.args.get("date_filter")

            # Filter by country
            q = db.query(Offer).filter(Offer.country.ilike(f"%{country_name}%"))
            
            if title:
                q = q.filter(Offer.title.ilike(f"%{title}%"))
            if company:
                q = q.filter(Offer.company.ilike(f"%{company}%"))
            if city:
                q = q.filter(Offer.location.ilike(f"%{city}%"))
            
            # Filtrage par date - use date_posted_parsed if available, fallback to created_at
            if date_filter:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                if date_filter == "today":
                    # For today, prefer date_posted_parsed but fallback to created_at
                    q = q.filter(
                        (Offer.date_posted_parsed >= today) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(today, datetime.min.time())))
                    )
                elif date_filter == "week":
                    week_ago = today - timedelta(days=7)
                    q = q.filter(
                        (Offer.date_posted_parsed >= week_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(week_ago, datetime.min.time())))
                    )
                elif date_filter == "month":
                    month_ago = today - timedelta(days=30)
                    q = q.filter(
                        (Offer.date_posted_parsed >= month_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(month_ago, datetime.min.time())))
                    )
                elif date_filter == "3months":
                    three_months_ago = today - timedelta(days=90)
                    q = q.filter(
                        (Offer.date_posted_parsed >= three_months_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(three_months_ago, datetime.min.time())))
                    )

            total = q.count()
            total_pages = max(math.ceil(total / 20) if total else 1, 1)
            offers = (
                q.order_by(Offer.date_posted_parsed.desc().nulls_last(), Offer.created_at.desc())
                 .offset((page - 1) * limit)
                 .limit(limit)
                 .all()
            )
            
            # Récupérer les listes pour les dropdowns (filtered by country)
            cities = [row[0] for row in db.query(Offer.location).filter(Offer.country.ilike(f"%{country_name}%")).distinct().all() if row[0]]
            countries = [row[0] for row in db.query(Offer.country).distinct().all() if row[0]]
            
            return render_template("index.html", 
                                 offers=offers, 
                                 page=page, 
                                 total_pages=total_pages,
                                 cities=sorted(cities),
                                 countries=sorted(countries),
                                 selected_country=country_name)
        except Exception as e:
            print(f"Error in country_offers: {e}")
            traceback.print_exc()
            return f"Error: {e}", 500
        finally:
            db.close()

    @app.route("/stats")
    @login_required
    def stats():
        db = get_db_session()
        try:
            total_offers = db.query(func.count(Offer.id)).scalar() or 0
            top_companies = (
                db.query(Offer.company, func.count(Offer.id))
                .group_by(Offer.company)
                .order_by(func.count(Offer.id).desc())
                .limit(5)
                .all()
            )
            offers_by_city = (
                db.query(Offer.location, func.count(Offer.id))
                .group_by(Offer.location)
                .order_by(func.count(Offer.id).desc())
                .limit(10)
                .all()
            )
            
            # Get scraping statistics
            recent_scraping_stats = (
                db.query(ScrapingStat)
                .order_by(ScrapingStat.execution_time.desc())
                .limit(20)  # Last 20 scraping jobs
                .all()
            )
            
            # Get summary statistics
            scraping_summary = (
                db.query(
                    ScrapingStat.country,
                    func.count(ScrapingStat.id).label('runs'),
                    func.sum(ScrapingStat.offers_found).label('total_found'),
                    func.sum(ScrapingStat.offers_inserted).label('total_inserted'),
                    func.avg(ScrapingStat.duration_seconds).label('avg_duration')
                )
                .group_by(ScrapingStat.country)
                .all()
            )
            
            return render_template(
                "stats.html",
                total_offers=total_offers,
                top_companies=top_companies,
                offers_by_city=offers_by_city,
                recent_scraping_stats=recent_scraping_stats,
                scraping_summary=scraping_summary
            )
        except Exception as e:
            print(f"Error in stats: {e}")
            traceback.print_exc()
            return f"Error: {e}", 500
        finally:
            db.close()

    # REST API
    @app.route("/api/offers", methods=["GET"])
    def api_offers():
        # For API, we'll still require authentication but check for API tokens
        # For simplicity, we'll allow access if user is logged in via session
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
            
        db = get_db_session()
        try:
            page = max(int(request.args.get("page", 1)), 1)
            limit = min(max(int(request.args.get("limit", 20)), 1), 100)
            title = request.args.get("title")
            company = request.args.get("company")
            city = request.args.get("city")
            country = request.args.get("country")
            date_filter = request.args.get("date_filter")

            q = db.query(Offer)
            if title:
                q = q.filter(Offer.title.ilike(f"%{title}%"))
            if company:
                q = q.filter(Offer.company.ilike(f"%{company}%"))
            if city:
                q = q.filter(Offer.location.ilike(f"%{city}%"))
            if country:
                q = q.filter(Offer.country.ilike(f"%{country}%"))
            
            # Filtrage par date - use date_posted_parsed if available, fallback to created_at
            if date_filter:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                if date_filter == "today":
                    # For today, prefer date_posted_parsed but fallback to created_at
                    q = q.filter(
                        (Offer.date_posted_parsed >= today) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(today, datetime.min.time())))
                    )
                elif date_filter == "week":
                    week_ago = today - timedelta(days=7)
                    q = q.filter(
                        (Offer.date_posted_parsed >= week_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(week_ago, datetime.min.time())))
                    )
                elif date_filter == "month":
                    month_ago = today - timedelta(days=30)
                    q = q.filter(
                        (Offer.date_posted_parsed >= month_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(month_ago, datetime.min.time())))
                    )
                elif date_filter == "3months":
                    three_months_ago = today - timedelta(days=90)
                    q = q.filter(
                        (Offer.date_posted_parsed >= three_months_ago) | 
                        ((Offer.date_posted_parsed.is_(None)) & (Offer.created_at >= datetime.combine(three_months_ago, datetime.min.time())))
                    )

            total = q.count()
            offers = (
                q.order_by(Offer.date_posted_parsed.desc().nulls_last(), Offer.created_at.desc())
                 .offset((page - 1) * limit)
                 .limit(limit)
                 .all()
            )
            data = [
                {
                    "id": o.id,
                    "title": o.title,
                    "company": o.company,
                    "location": o.location,
                    "country": o.country,
                    "date_posted": o.date_posted,
                    "date_posted_parsed": o.date_posted_parsed.isoformat() if o.date_posted_parsed is not None else None,
                    "link": o.link,
                    "created_at": o.created_at.isoformat(),
                }
                for o in offers
            ]
            return jsonify({"page": page, "limit": limit, "total": total, "items": data})
        except Exception as e:
            print(f"Error in api_offers: {e}")
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/scrape", methods=["POST"])  # manual refresh
    def api_scrape():
        # For API, we'll still require authentication but check for API tokens
        # For simplicity, we'll allow access if user is logged in via session
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
            
        try:
            # Get country parameter from form or default to Morocco
            country = request.form.get("country", "Maroc")
            # Use only 1 page for manual scraping to be gentle on the server
            inserted = run_scrape_job(max_pages=1, country=country)
            if request.accept_mimetypes.accept_html and not request.is_json:
                # Redirect back to country-specific page in HTML contexts
                return redirect(url_for("country_offers", country_name=country))
            return jsonify({"inserted": inserted})
        except Exception as e:
            print(f"Error in api_scrape: {e}")
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route("/offers-test")
    @login_required
    def offers_test():
        """Test endpoint to display existing offers without scraping"""
        db = get_db_session()
        try:
            # Get a few existing offers
            offers = db.query(Offer).order_by(Offer.created_at.desc()).limit(10).all()
            
            return render_template('index.html', 
                                 offers=offers, 
                                 page=1, 
                                 total_pages=1,
                                 cities=[],
                                 countries=[],
                                 show_all_offers=True)
        except Exception as e:
            logger.error(f"Offers test error: {e}")
            flash("Error loading offers", "error")
            return redirect(url_for('index'))
        finally:
            db.close()

    @app.route("/test-db")
    def test_db():
        """Test route to check database connectivity and data"""
        db = get_db_session()
        try:
            # Count offers
            offer_count = db.query(Offer).count()
            # Get recent offers
            recent_offers = db.query(Offer).order_by(Offer.created_at.desc()).limit(5).all()
            
            return jsonify({
                "offer_count": offer_count,
                "recent_offers": [
                    {
                        "id": o.id,
                        "title": o.title,
                        "company": o.company,
                        "created_at": o.created_at.isoformat() if o.created_at is not None else None
                    }
                    for o in recent_offers
                ]
            })
        except Exception as e:
            logger.error(f"Database test error: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    @app.route("/test-scrape")
    @login_required
    def test_scrape():
        """Test route to manually trigger scraping"""
        try:
            # Use very conservative settings for testing
            inserted = run_scrape_job(max_pages=1, country="Maroc")
            return jsonify({
                "inserted": inserted,
                "message": f"Successfully scraped and inserted {inserted} offers",
                "note": "Check logs for detailed scraping information"
            })
        except Exception as e:
            logger.error(f"Scraping test error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": str(e),
                "message": "Scraping failed. Check logs for details."
            }), 500

    @app.route("/test-scrape-verbose")
    @login_required
    def test_scrape_verbose():
        """Test route to manually trigger scraping with verbose output"""
        try:
            # Import here to avoid circular imports
            from scheduler import run_scrape_job
            
            # Use verbose settings for testing
            inserted = run_scrape_job(max_pages=1, country="Maroc")
            return jsonify({
                "status": "success",
                "inserted": inserted,
                "message": f"Scraping completed. Inserted {inserted} offers.",
                "next_steps": "Check logs for detailed scraping information"
            })
        except Exception as e:
            logger.error(f"Verbose scraping test error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "error": str(e),
                "message": "Scraping failed. Check logs for details."
            }), 500

    @app.route("/test-scrape-with-proxy")
    @login_required
    def test_scrape_with_proxy():
        """Test route to manually trigger scraping with proxy support"""
        proxy = request.args.get('proxy', '')
        try:
            # Get proxy from environment variable for testing
            if proxy:
                # Temporarily set the proxy environment variable
                os.environ['SCRAPER_PROXIES'] = proxy
                print(f"Testing with proxy: {proxy}")
            
            # Import here to avoid circular imports
            from scheduler import run_scrape_job
            
            # Use verbose settings for testing
            inserted = run_scrape_job(max_pages=1, country="Maroc")
            
            # Clean up
            if proxy:
                os.environ.pop('SCRAPER_PROXIES', None)
            
            return jsonify({
                "status": "success",
                "inserted": inserted,
                "message": f"Scraping completed with proxy. Inserted {inserted} offers.",
                "proxy_used": proxy if proxy else "None"
            })
        except Exception as e:
            logger.error(f"Proxy scraping test error: {e}")
            import traceback
            traceback.print_exc()
            # Clean up
            if proxy:
                os.environ.pop('SCRAPER_PROXIES', None)
            return jsonify({
                "status": "error",
                "error": str(e),
                "message": "Scraping failed. Check logs for details."
            }), 500

    @app.route("/scheduler-test")
    @login_required
    def scheduler_test():
        """Test endpoint to check scheduler status"""
        try:
            from scheduler import get_next_run_times
            next_runs = get_next_run_times(scheduler)
            
            # Convert datetime objects to strings for JSON
            next_runs_str = {}
            for job_id, next_run_time in next_runs.items():
                next_runs_str[job_id] = next_run_time.isoformat() if next_run_time else None
            
            return jsonify({
                "scheduler_status": "running",
                "next_runs": next_runs_str,
                "message": "Scheduler is working correctly"
            })
        except Exception as e:
            logger.error(f"Scheduler test error: {e}")
            return jsonify({
                "scheduler_status": "error",
                "error": str(e),
                "message": "Scheduler has issues"
            }), 500

    @app.route("/health")
    def health_check():
        """Simple health check to verify database connectivity"""
        db = get_db_session()
        try:
            # Count offers
            offer_count = db.query(Offer).count()
            # Count users
            user_count = db.query(User).count()
            
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "offers": offer_count,
                "users": user_count,
                "message": "Application is running correctly"
            })
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "message": "Database connection failed"
            }), 500
        finally:
            db.close()

    @app.route("/debug-info")
    @login_required
    def debug_info():
        """Debug endpoint to show application status"""
        db = get_db_session()
        try:
            # Get database info
            offer_count = db.query(Offer).count()
            user_count = db.query(User).count()
            
            # Get recent offers
            recent_offers = db.query(Offer).order_by(Offer.created_at.desc()).limit(5).all()
            
            # Check scheduler
            try:
                from scheduler import get_next_run_times
                next_runs = get_next_run_times(scheduler)
                scheduler_status = "Running"
            except Exception as e:
                next_runs = {}
                scheduler_status = f"Error: {e}"
            
            return jsonify({
                "application": "Internship Tracker",
                "database": {
                    "status": "Connected",
                    "offers_count": offer_count,
                    "users_count": user_count
                },
                "scheduler": {
                    "status": scheduler_status,
                    "next_runs": {k: v.isoformat() if v else None for k, v in next_runs.items()}
                },
                "session": {
                    "user_id": session.get('user_id'),
                    "user_email": session.get('user_email')
                }
            })
        except Exception as e:
            logger.error(f"Debug info error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": str(e),
                "message": "Failed to retrieve debug information"
            }), 500
        finally:
            db.close()

    # Make sure we return the app
    return app


# This is required for Gunicorn to work properly
if __name__ == "__main__":
    app = create_app()
    # Use the PORT environment variable for Render, default to 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)