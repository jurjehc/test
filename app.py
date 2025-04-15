import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash

from models import db, User, Race, RaceEntry
from forms import LoginForm, RegistrationForm, RaceForm, RaceEntryForm

# App initialization
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev',
    SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'race_timer.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
@app.before_first_request
def create_tables():
    db.create_all()
    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('adminpassword')
        db.session.add(admin)
        db.session.commit()

# Routes
@app.route('/')
def index():
    upcoming_races = Race.query.filter(Race.date >= datetime.utcnow().date(), Race.is_active == True).order_by(Race.date).limit(5).all()
    return render_template('index.html', races=upcoming_races)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid username or password')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

# Public routes
@app.route('/races')
def races():
    upcoming_races = Race.query.filter(Race.date >= datetime.utcnow().date(), Race.is_active == True).order_by(Race.date).all()
    past_races = Race.query.filter(Race.date < datetime.utcnow().date(), Race.is_active == True).order_by(Race.date.desc()).all()
    return render_template('public/races.html', upcoming_races=upcoming_races, past_races=past_races)

@app.route('/race/<int:race_id>')
def race_details(race_id):
    race = Race.query.get_or_404(race_id)
    return render_template('public/race_details.html', race=race)

@app.route('/race/<int:race_id>/signup', methods=['GET', 'POST'])
@login_required
def race_signup(race_id):
    race = Race.query.get_or_404(race_id)
    
    # Check if race is in the future and active
    if race.date < datetime.utcnow().date() or not race.is_active:
        flash('Registration for this race is closed.')
        return redirect(url_for('race_details', race_id=race_id))
    
    # Check if user is already registered
    existing_entry = RaceEntry.query.filter_by(race_id=race_id, user_id=current_user.id).first()
    if existing_entry:
        flash('You are already registered for this race.')
        return redirect(url_for('race_details', race_id=race_id))
    
    form = RaceEntryForm()
    if form.validate_on_submit():
        # Generate bib number
        last_entry = RaceEntry.query.filter_by(race_id=race_id).order_by(RaceEntry.bib_number.desc()).first()
        bib_number = 1 if not last_entry else last_entry.bib_number + 1
        
        entry = RaceEntry(
            bib_number=bib_number,
            race_id=race_id,
            user_id=current_user.id
        )
        db.session.add(entry)
        db.session.commit()
        flash('You have successfully registered for this race!')
        return redirect(url_for('race_details', race_id=race_id))
    
    return render_template('public/signup.html', race=race, form=form)

@app.route('/race/<int:race_id>/results')
def race_results(race_id):
    race = Race.query.get_or_404(race_id)
    results = RaceEntry.query.filter_by(race_id=race_id, status='finished').join(User).order_by(RaceEntry.elapsed_time).all()
    return render_template('public/results.html', race=race, results=results)

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required.')
        return redirect(url_for('index'))
    
    active_races = Race.query.filter_by(is_active=True).order_by(Race.date).all()
    upcoming_races = [race for race in active_races if race.date >= datetime.utcnow().date()]
    ongoing_races = [race for race in active_races if race.is_started and not all(entry.status == 'finished' for entry in race.entries)]
    
    return render_template('admin/dashboard.html', 
                           upcoming_races=upcoming_races, 
                           ongoing_races=ongoing_races)

@app.route('/admin/races')
@login_required
def admin_races():
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required.')
        return redirect(url_for('index'))
    
    races = Race.query.order_by(Race.date.desc()).all()
    return render_template('admin/races.html', races=races)

@app.route('/admin/race/new', methods=['GET', 'POST'])
@login_required
def create_race():
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required.')
        return redirect(url_for('index'))
    
    form = RaceForm()
    if form.validate_on_submit():
        race = Race(
            name=form.name.data,
            description=form.description.data,
            location=form.location.data,
            date=form.date.data,
            start_time=form.start_time.data,
            distance=form.distance.data,
            max_participants=form.max_participants.data,
            is_active=True
        )
        db.session.add(race)
        db.session.commit()
        flash('Race created successfully!')
        return redirect(url_for('admin_races'))
    
    return render_template('admin/race_form.html', form=form, title='Create Race')

@app.route('/admin/race/<int:race_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_race(race_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required.')
        return redirect(url_for('index'))
    
    race = Race.query.get_or_404(race_id)
    form = RaceForm(obj=race)
    
    if form.validate_on_submit():
        form.populate_obj(race)
        db.session.commit()
        flash('Race updated successfully!')
        return redirect(url_for('admin_races'))
    
    return render_template('admin/race_form.html', form=form, title='Edit Race')

@app.route('/admin/race/<int:race_id>/start', methods=['POST'])
@login_required
def start_race(race_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin privileges required'}), 403
    
    race = Race.query.get_or_404(race_id)
    
    if race.is_started:
        return jsonify({'success': False, 'message': 'Race has already started'}), 400
    
    now = datetime.utcnow()
    race.is_started = True
    race.start_timestamp = now
    
    # Update all registered entries to started status
    for entry in race.entries:
        entry.status = 'started'
        entry.start_time = now
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Race started successfully'})

@app.route('/admin/race/<int:race_id>/finish', methods=['POST'])
@login_required
def finish_runner(race_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin privileges required'}), 403
    
    race = Race.query.get_or_404(race_id)
    bib_number = request.form.get('bib_number')
    
    if not race.is_started:
        return jsonify({'success': False, 'message': 'Race has not started yet'}), 400
    
    entry = RaceEntry.query.filter_by(race_id=race_id, bib_number=bib_number).first()
    
    if not entry:
        return jsonify({'success': False, 'message': f'No runner with bib number {bib_number}'}), 404
    
    if entry.status == 'finished':
        return jsonify({'success': False, 'message': 'Runner has already finished'}), 400
    
    entry.status = 'finished'
    entry.finish_time = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Runner {bib_number} finished',
        'elapsed_time': entry.elapsed_time
    })

@app.route('/admin/race/<int:race_id>/entries')
@login_required
def race_entries(race_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required.')
        return redirect(url_for('index'))
    
    race = Race.query.get_or_404(race_id)
    entries = RaceEntry.query.filter_by(race_id=race_id).join(User).all()
    
    return render_template('admin/race_entries.html', race=race, entries=entries)

@app.route('/admin/race/<int:race_id>/timing')
@login_required
def race_timing(race_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required.')
        return redirect(url_for('index'))
    
    race = Race.query.get_or_404(race_id)
    entries = RaceEntry.query.filter_by(race_id=race_id).join(User).all()
    
    return render_template('admin/race_timing.html', race=race, entries=entries)

if __name__ == '__main__':
    app.run(debug=True)