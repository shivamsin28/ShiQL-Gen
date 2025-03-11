from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import bcrypt


app = Flask(__name__)
app.secret_key = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    
    def __init__(self, name, username, email, password):
        self.name = name
        self.username = username
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
    def __repr__(self):
        return '<User %r>' % self.username
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

with app.app_context():
    db.create_all()
    


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(username=username).first() or User.query.filter_by(email=username).first()
        if user:
            if user.check_password(password):
                session['user'] = user.username
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password')
        flash('Invalid username or password')
    return render_template('login.html')

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        try:
            user = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
            if user:
                flash('User already exists')
                return render_template('register.html')
        except:
            pass
        user = User(name, username, email, password)
        db.session.add(user)
        db.session.commit()
        flash('User added successfully')
        return redirect(url_for('login'))
    return render_template('register.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)