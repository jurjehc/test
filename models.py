from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    race_entries = db.relationship('RaceEntry', backref='runner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Race(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    distance = db.Column(db.Float)  # in kilometers
    max_participants = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    is_started = db.Column(db.Boolean, default=False)
    start_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    entries = db.relationship('RaceEntry', backref='race', lazy=True)
    
    def __repr__(self):
        return f'<Race {self.name}>'


class RaceEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bib_number = db.Column(db.Integer, nullable=False)
    race_id = db.Column(db.Integer, db.ForeignKey('race.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registration_time = db.Column(db.DateTime, default=datetime.utcnow)
    start_time = db.Column(db.DateTime)  # When the race started
    finish_time = db.Column(db.DateTime)  # When runner finished
    status = db.Column(db.String(20), default='registered')  # registered, started, finished, DNF
    
    @property
    def elapsed_time(self):
        if self.start_time and self.finish_time:
            return (self.finish_time - self.start_time).total_seconds()
        return None
    
    def __repr__(self):
        return f'<RaceEntry {self.bib_number}>'