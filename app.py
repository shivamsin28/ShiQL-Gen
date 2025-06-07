from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import bcrypt
from utils.sql_query_generator import SQLQueryGenerator
import google.generativeai as genai
import os 
from dotenv import load_dotenv
from functools import wraps 
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import sqlite3
import re
import pandas as pd
from sqlalchemy import create_engine, text
from instance.create_db import create_and_populate_database

# Initialize Flask app
app = Flask(__name__) 
app.secret_key = os.urandom(24) 
app.config['SESSION_TYPE'] = 'filesystem' 
Session(app) 

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")

if not API_KEY: 
    raise ValueError("Please set the GOOGLE_API_KEY environment variable in your .env file") 

# Configure Gemini AI
genai.configure(api_key=API_KEY) 
gen_config = genai.GenerationConfig( 
    max_output_tokens=2048, 
    temperature=0.1, 
    top_p=0.9 
)
model = genai.GenerativeModel("gemini-2.0-flash-exp", generation_config=gen_config) 



# Database configuration
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
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            if user.check_password(password):
                session['user'] = user.username
                return redirect(url_for('generate_query'))
            else:
                flash('Invalid username or password')
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/generate_query')
def generate_query():
    if 'user' not in session:
        flash('Please login to access the query generator')
        return redirect(url_for('login'))
    return render_template('generate_query.html', username=session['user'])

@app.route("/dashboard")
def dashboard():
    if 'user' not in session:
        flash('Please login to access the dashboard')
        return redirect(url_for('login'))
    return render_template("dashboard.html", username=session['user'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out successfully')
    return redirect(url_for('login'))

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

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection(db_type, db_params):
    try:
        if db_type == "sqlite":
            conn = sqlite3.connect(db_params["database"])
            return conn
        elif db_type == "mysql":
            engine = create_engine(
                f"mysql+mysqlconnector://{db_params['username']}:{db_params['password']}@{db_params['host']}/{db_params['database']}")
            return engine.connect()
        elif db_type == "postgresql":
            engine = create_engine(
                f"postgresql+psycopg2://{db_params['username']}:{db_params['password']}@{db_params['host']}/{db_params['database']}")
            return engine.connect()
    except Exception as e:
        flash(f"Connection error: {str(e)}", "error")
        return None

def generate_sql(prompt, schema=None, dialect="sqlite", purpose="query"):
    if purpose == "create_table":
        full_prompt = f"Generate a CREATE TABLE SQL statement for {dialect} with the following schema:\n{schema}"
    elif purpose == "insert":
        full_prompt = f"Generate an INSERT INTO SQL statement for {dialect} for table {schema} with the following data:\n{prompt}"
    else:
        full_prompt = f"Given the following schema:\n{schema}\nand instruction:\n{prompt}\nGenerate a SQL query for {dialect}."
    
    try:
        response = model.generate_content(full_prompt)
        return clean_sql(response.text)
    except Exception as e:
        return f"Error: {str(e)}"

def clean_sql(sql_query):
    sql_query = re.sub(r'```[a-z]*\n', '', sql_query, flags=re.IGNORECASE)
    sql_query = re.sub(r'```', '', sql_query, flags=re.IGNORECASE)
    sql_query = re.sub(r'^sql', '', sql_query, flags=re.IGNORECASE).strip()
    return sql_query

def execute_sql(sql_query, db_type, db_params, return_results=True):
    conn = None
    try:
        conn = get_db_connection(db_type, db_params)
        if not conn:
            return "Failed to connect to database"
        
        # Execute the query first (needed for all query types)
        if db_type == "sqlite":
            conn.execute(sql_query)
            conn.commit()
        else:
            conn.execute(text(sql_query))
            conn.commit()
        
        # For SELECT queries or if results are needed after UPDATE/DELETE
        if return_results:
            # For UPDATE or DELETE queries, fetch the updated data
            if sql_query.strip().upper().startswith(('UPDATE', 'DELETE')):
                table_name = re.search(r'(UPDATE|DELETE FROM)\s+(\w+)', sql_query, re.IGNORECASE).group(2)
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            else:
                df = pd.read_sql_query(sql_query, conn)
            return df.to_html(classes='table table-striped', index=False)
        else:
            return "Query executed successfully"
    except Exception as e:
        return f"Error executing query: {str(e)}"
    finally:
        if conn:
            conn.close()

@app.route('/connect_database', methods=['POST'])
def connect_database():
    db_type = request.form['db_type']
    db_params = {}
    
    if db_type == 'sqlite':
        db_params['database'] = request.form['database']
    else:
        db_params['host'] = request.form['host']
        db_params['username'] = request.form['username']
        db_params['password'] = request.form['password']
        db_params['database'] = request.form['database_name']

    conn = get_db_connection(db_type, db_params)
    if conn:
        conn.close()
        session['db_connected'] = True
        session['db_type'] = db_type
        session['connection_params'] = db_params
        flash('Successfully connected to database!', 'success')
    else:
        flash('Failed to connect to database', 'error')
    
    return redirect(url_for('generate_query'))

@app.route('/create_table', methods=['POST'])
def create_table():
    if not session.get('db_connected'):
        flash('Please connect to a database first', 'error')
        return redirect(url_for('generate_query'))
    
    table_name = request.form['table_name']
    table_schema = request.form['table_schema']
    
    create_query = generate_sql(None, f"CREATE TABLE {table_name} ({table_schema})", 
                              session['db_type'], "create_table")
    result = execute_sql(create_query, session['db_type'], 
                        session['connection_params'], False)
    
    if "Error" not in str(result):
        session['table_created'] = True
        session['current_table'] = table_name
        flash(f"Table '{table_name}' created successfully!", 'success')
    else:
        flash(result, 'error')
    
    return redirect(url_for('generate_query'))

@app.route('/insert_data', methods=['POST'])
def insert_data():
    if not session.get('table_created'):
        flash('Please create a table first', 'error')
        return redirect(url_for('generate_query'))
    
    insert_prompt = request.form['insert_prompt']
    insert_query = generate_sql(insert_prompt, session['current_table'], 
                              session['db_type'], "insert")
    result = execute_sql(insert_query, session['db_type'], 
                        session['connection_params'], False)
    
    if "Error" not in str(result):
        flash('Data inserted successfully!', 'success')
    else:
        flash(result, 'error')
    
    return redirect(url_for('generate_query'))

@app.route('/execute_query', methods=['POST'])
def execute_query():
    if not session.get('table_created'):
        flash('Please create a table first', 'error')
        return redirect(url_for('generate_query'))
    
    query_prompt = request.form['query_prompt']
    query = generate_sql(query_prompt, session['current_table'], 
                        session['db_type'], "query")
    result = execute_sql(query, session['db_type'], session['connection_params'])
    
    if "Error" not in str(result):
        session['query_result'] = result
        session['generated_sql'] = query
        flash('Query executed successfully!', 'success')
    else:
        flash(result, 'error')
        session['query_result'] = None
        session['generated_sql'] = None
    
    return redirect(url_for('generate_query'))


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)






    