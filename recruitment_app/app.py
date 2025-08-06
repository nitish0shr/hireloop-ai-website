"""
Simple recruitment automation web application for HireLoop AI.

This Flask-based app allows clients to submit job descriptions, automatically
generates a list of candidate profiles (dummy data for demonstration), and
stores everything in a SQLite database. Clients can view all submitted roles
and review the generated candidate lists.

Note: This is a minimal proof-of-concept for demonstration purposes. In a
production system you would integrate with real sourcing tools (e.g., Apollo
API), use GPT models to parse the job description and score candidates, and
securely deploy the application on a platform like Heroku, Render or AWS.
"""

import os
import random
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash


app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key'
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'database.db')


def get_db_connection():
    """Open a connection to the SQLite database and return the connection."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database tables if they don't already exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Create table for roles
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date_created TEXT NOT NULL
        )
        """
    )
    # Create table for candidates
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            current_title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            linkedin TEXT NOT NULL,
            match_reason TEXT NOT NULL,
            fit_score INTEGER,
            culture_score INTEGER,
            experience_score INTEGER,
            FOREIGN KEY(role_id) REFERENCES roles(id)
        )
        """
    )
    conn.commit()
    conn.close()


def generate_dummy_candidates(role_title: str, num_candidates: int = 10):
    """Generate a list of dummy candidate dictionaries for demonstration.

    Each candidate has randomised attributes. In a real implementation this
    function would query external databases or use GPT to score candidates.

    Args:
        role_title: The job title extracted from the job description.
        num_candidates: Number of candidate profiles to generate.

    Returns:
        List[dict]: A list of candidate dictionaries.
    """
    first_names = [
        'Aarav', 'Liam', 'Emma', 'Noah', 'Olivia', 'Aria', 'Ethan', 'Mia',
        'Sophia', 'Lucas', 'Aaliyah', 'Zara', 'Jayden', 'Alina', 'David'
    ]
    last_names = [
        'Patel', 'Johnson', 'Singh', 'Garcia', 'Kumar', 'Williams', 'Chen',
        'Khan', 'Brown', 'Rodriguez', 'Ali', 'Davis', 'Nguyen', 'Lee', 'Shah'
    ]
    companies = ['TechNova', 'DataSphere', 'InnovateX', 'CodeWorks', 'NextGen']
    locations = ['San Francisco, CA', 'Austin, TX', 'Bangalore, India', 'Dubai, UAE', 'Remote']
    match_reasons = [
        'Relevant experience in similar role',
        'Strong technical skills matching JD',
        'Excellent cultural alignment',
        'Recent experience at high-growth startup',
        'Highly recommended by references'
    ]

    candidates = []
    for _ in range(num_candidates):
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{first} {last}"
        candidate = {
            'name': name,
            'current_title': random.choice([
                f"Senior {role_title}",
                f"{role_title} II",
                f"Lead {role_title}",
                f"{role_title} Specialist",
                f"{role_title} Consultant"
            ]),
            'company': random.choice(companies),
            'location': random.choice(locations),
            'linkedin': f"https://linkedin.com/in/{first.lower()}{last.lower()}",
            'match_reason': random.choice(match_reasons),
            'fit_score': random.randint(60, 100),
            'culture_score': random.randint(60, 100),
            'experience_score': random.randint(60, 100),
        }
        candidates.append(candidate)
    return candidates


@app.before_first_request
def startup():
    """Initialize database before handling the first request."""
    init_db()


@app.route('/')
def index():
    """Home page showing all submitted roles and candidate counts."""
    conn = get_db_connection()
    roles = conn.execute(
        'SELECT r.id, r.title, r.date_created, COUNT(c.id) AS candidate_count '
        'FROM roles r LEFT JOIN candidates c ON r.id = c.role_id '
        'GROUP BY r.id ORDER BY r.date_created DESC'
    ).fetchall()
    conn.close()
    return render_template('index.html', roles=roles)


@app.route('/role/new', methods=['GET', 'POST'])
def new_role():
    """Form to create a new role and generate candidate list."""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if not title or not description:
            flash('Please provide both a title and a job description.', 'danger')
            return redirect(url_for('new_role'))

        # Save role to database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO roles (title, description, date_created) VALUES (?, ?, ?)',
            (title, description, datetime.utcnow().isoformat())
        )
        role_id = cur.lastrowid
        conn.commit()

        # Generate dummy candidates and save to database
        candidates = generate_dummy_candidates(title, num_candidates=10)
        for candidate in candidates:
            cur.execute(
                'INSERT INTO candidates '
                '(role_id, name, current_title, company, location, linkedin, match_reason, '
                'fit_score, culture_score, experience_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    role_id, candidate['name'], candidate['current_title'], candidate['company'],
                    candidate['location'], candidate['linkedin'], candidate['match_reason'],
                    candidate['fit_score'], candidate['culture_score'], candidate['experience_score']
                )
            )
        conn.commit()
        conn.close()

        flash('Role created and candidates generated successfully!', 'success')
        return redirect(url_for('view_role', role_id=role_id))

    return render_template('new_role.html')


@app.route('/role/<int:role_id>')
def view_role(role_id):
    """View details for a specific role and its candidate list."""
    conn = get_db_connection()
    role = conn.execute(
        'SELECT * FROM roles WHERE id = ?', (role_id,)
    ).fetchone()
    candidates = conn.execute(
        'SELECT * FROM candidates WHERE role_id = ? ORDER BY fit_score DESC', (role_id,)
    ).fetchall()
    conn.close()
    if role is None:
        flash('Role not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('role.html', role=role, candidates=candidates)


if __name__ == '__main__':
    app.run(debug=True)
