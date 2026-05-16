from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random string

# ============================================
# DATABASE CONNECTION
# ============================================
def get_db_connection():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row
    return conn

# ============================================
# DATABASE INITIALIZATION
# ============================================
def init_db():
    with get_db_connection() as conn:
        # Create users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # Create books table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()

init_db()

# ============================================
# HELPER FUNCTIONS
# ============================================
def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator to protect routes - require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ROUTE: HOME PAGE
# ============================================
@app.route('/')
def index():
    return render_template('index.html')

# ============================================
# ROUTE: REGISTER
# ============================================
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        error = None

        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'

        if error is None:
            try:
                conn = get_db_connection()
                conn.execute(
                    'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                    (username, email, hash_password(password))
                )
                conn.commit()
                conn.close()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                error = 'Username or email already exists.'

        return render_template('register.html', error=error)
    
    return render_template('register.html')

# ============================================
# ROUTE: LOGIN
# ============================================
@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user is None:
            error = 'Invalid username.'
        elif hash_password(password) != user['password']:
            error = 'Invalid password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('books'))

        return render_template('login.html', error=error)
    
    return render_template('login.html')

# ============================================
# ROUTE: LOGOUT
# ============================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============================================
# ROUTE: VIEW ALL BOOKS (LOGIN REQUIRED)
# ============================================
@app.route('/books')
@login_required
def books():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books WHERE user_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('books.html', books=books)

# ============================================
# ROUTE: ADD NEW BOOK (LOGIN REQUIRED)
# ============================================
@app.route('/add', methods=('GET', 'POST'))
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        error = None

        if not title:
            error = 'Title is required.'
        elif not author:
            error = 'Author is required.'

        if error is None:
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO books (title, author, year, user_id) VALUES (?, ?, ?, ?)',
                (title, author, year, session['user_id'])
            )
            conn.commit()
            conn.close()
            return redirect(url_for('books'))

        return render_template('add_book.html', error=error)
    
    return render_template('add_book.html')

# ============================================
# ROUTE: DELETE BOOK
# ============================================
@app.route('/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM books WHERE id = ? AND user_id = ?', (book_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('books'))

# ============================================
# RUN SERVER
# ============================================
if __name__ == '__main__':
    app.run(debug=True)