# Internship Tracker - Flask + Indeed Scraper

## Overview

This project is a complete Flask web application that scrapes internship offers from Indeed, stores them in a database, and provides a vibrant, high-impact web interface and REST API with pagination, filters, and basic statistics. A background scheduler automatically refreshes the offers every hour, and you can also trigger scraping manually from the UI or via the API.

## Visual Design Overhaul

The application has been completely redesigned with a high-impact, vibrant, and modern aesthetic, moving away from the minimal, white aesthetic to a more engaging experience:

### New Core Color Palette
- **Primary Accent Color**: Vibrant Cyan/Teal (#38a3a5) for large background blocks
- **Secondary/Action Color**: High-visibility Vibrant Yellow (#ffc107) for all primary call-to-action buttons
- **Text/Background**: White and dark gray/black (#333333) for contrast

### Landing Page Transformation
- **Hero Block**: Bold Primary Accent Color background on the top half of the page
- **Pattern**: Subtle dynamic geometric background pattern for texture
- **Typography**: Significantly larger, bolder white text on colored background
- **Country Cards**: Pure white cards that visually "float" over the colored header

### Authentication Pages Redesign
- **Two-Column Layout**: Split layout similar to modern web applications
- **Left Column**: Primary Accent Color background with branding and features
- **Right Column**: Clean white card for login/registration forms
- **Buttons**: Secondary/Action Color for maximum visibility

### General Style Upgrades
- **Navigation**: Primary Accent Color navbar with white text
- **Job Listings**: Secondary/Action Color for filter buttons, Primary Accent for card borders
- **Typography**: Bold, modern sans-serif font throughout for energetic look

## Features

- **Scraping** (Indeed only for now): title, company, location, date_posted, link
- **De-duplication**: only new offers (unique on link) are inserted
- **Scheduler**: APScheduler job runs scraping every hour for 5 countries
- **Manual refresh**: POST /api/scrape or UI button
- **Database**: SQLite by default (easily switchable to PostgreSQL)
- **Modern Web UI**: Flask + Jinja2 + Custom CSS with responsive design
- **REST API**:
  - GET /api/offers?page=1&limit=20
  - GET /api/offers?company=OCP&city=Casablanca
  - POST /api/scrape
- **Stats dashboard**: total offers, top 5 companies, offers by city
- **User Authentication**: Secure login and registration system

## Deployment

This application can be deployed to various platforms. Below are instructions for popular deployment options:

### Deploy to Render (Recommended)

1. Fork this repository to your GitHub account
2. Sign up at [Render](https://render.com/) (free tier available)
3. Click "New+" and select "Web Service"
4. Connect your GitHub account and select your forked repository
5. Configure the service:
   - Name: internship-scraper
   - Environment: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn --bind 0.0.0.0:$PORT app:create_app()`
6. Add environment variables (optional):
   - SECRET_KEY: A random string for security (default is auto-generated)
7. Click "Create Web Service"

The application will automatically deploy and be available at https://your-app-name.onrender.com

### Deploy to Heroku

1. Install the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Login to Heroku: `heroku login`
3. Create a new app: `heroku create your-app-name`
4. Set the stack to container: `heroku stack:set container`
5. Push to Heroku: `git push heroku main`
6. Open the app: `heroku open`

### Deploy to PythonAnywhere

1. Sign up at [PythonAnywhere](https://www.pythonanywhere.com/) (free tier available)
2. Upload your project files
3. Create a virtual environment and install requirements:
   ```
   mkvirtualenv internship_scraper
   pip install -r requirements.txt
   ```
4. Configure the web app in the PythonAnywhere dashboard
5. Set the WSGI file to point to your application

## Project Structure

```
internship_tracker/
- app.py
- scraper/
  - indeed_scraper.py
- models.py
- database.py
- forms.py
- templates/
  - index.html
  - country_selector.html
  - login.html
  - register.html
  - stats.html
- static/
  - styles.css
- scheduler.py
- requirements.txt
- README.md
```

## Quickstart

1) Create and activate a virtual environment (Windows PowerShell):

```bash
python -m venv venv
venv\Scripts\Activate.ps1
```

2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Run the app:

```bash
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Manual Scrape

From the UI: Click "Actualiser les offres" on any country page.

From the API:

```bash
curl -X POST http://127.0.0.1:5000/api/scrape
```

## Environment Variables (Optional)

- DATABASE_URL: Set to use PostgreSQL instead of SQLite, e.g. postgresql+psycopg2://user:pass@localhost:5432/dbname
- SECRET_KEY: Set to a random string for security (auto-generated by default)

## Design Details

### Color Scheme Implementation
- **Primary (#38a3a5)**: Used for navigation bars, hero sections, and left columns
- **Secondary (#ffc107)**: Used for all primary action buttons (login, filter, etc.)
- **Text (#333333)**: High contrast dark gray for readability
- **Backgrounds**: Clean white for content areas

### Layout Improvements
- **Landing Page**: Dynamic hero section with floating country cards
- **Authentication**: Two-column layout with brand messaging
- **Job Listings**: Enhanced card design with accent borders
- **Statistics**: Vibrant data visualization with clear hierarchy

### UI Component Enhancements
- **Buttons**: Consistent styling with hover effects and shadows
- **Forms**: Modern input fields with focus states
- **Cards**: Subtle animations and shadows for depth
- **Navigation**: Clear visual hierarchy with hover effects

## Notes

- The Indeed site may throttle or block scraping. This demo uses polite headers and basic HTML parsing via BeautifulSoup.
- Adjust the number of pages in the scheduler or API call if needed.
- The application now includes comprehensive logging for monitoring scraping jobs.