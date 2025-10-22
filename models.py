from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, Date, Boolean
from database import Base
from werkzeug.security import generate_password_hash, check_password_hash


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)  # Nouveau champ pays
    date_posted = Column(String(100), nullable=True)
    date_posted_parsed = Column(Date, nullable=True)  # Date parsée pour filtrage
    link = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("link", name="uq_offers_link"),
    )

    def __repr__(self):
        return f"<Offer(id={self.id}, title='{self.title}', company='{self.company}')>"


class ScrapingStat(Base):
    __tablename__ = "scraping_stats"

    id = Column(Integer, primary_key=True, index=True)
    country = Column(String(100), nullable=False)
    offers_found = Column(Integer, default=0)
    offers_inserted = Column(Integer, default=0)
    execution_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration_seconds = Column(Integer, default=0)

    def __repr__(self):
        return f"<ScrapingStat(id={self.id}, country='{self.country}', offers_found={self.offers_found}, execution_time='{self.execution_time}')>"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        # Ensure we're working with the string value of password_hash
        try:
            return check_password_hash(str(self.password_hash), password)
        except:
            return False
            
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"