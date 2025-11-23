import os
from flask import Flask, render_template, request
import mysql.connector

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

# Normalize the path to handle Windows paths correctly
TEMPLATE_DIR = os.path.normpath(TEMPLATE_DIR)

# Verify template directory exists
if not os.path.exists(TEMPLATE_DIR):
    raise FileNotFoundError(f"Template directory not found: {TEMPLATE_DIR}")

# Initialize Flask app with explicit template folder path
app = Flask(__name__, template_folder=TEMPLATE_DIR, root_path=BASE_DIR)

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "081206",
    "database": "sgpa_db"
}

# --- Initialize database ---
def init_db():
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )
    cur = conn.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS sgpa_db")
    cur.close()
    conn.close()

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    # Drop table if exists to ensure correct schema
    cur.execute("DROP TABLE IF EXISTS sgpa_records")
    # Create table with correct schema
    cur.execute("""
        CREATE TABLE sgpa_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            rollno VARCHAR(50),
            department VARCHAR(100),
            semester VARCHAR(50),
            subject VARCHAR(100),
            credit INT,
            grade VARCHAR(10),
            points INT,
            sgpa FLOAT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


# --- Grade Point Mapping ---
GRADE_POINTS = {
    "O": 10,
    "A+": 9,
    "A": 8,
    "B+": 7,
    "B": 6,
    "C": 5,
    "F": 0
}


# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        name = request.form.get('name')
        rollno = request.form.get('rollno') 
        department = request.form.get('department')
        semester = request.form.get('semester')

        subjects = request.form.getlist('subject')
        credits = request.form.getlist('credit')
        grades = request.form.getlist('grade')

        total_credits = 0
        weighted_sum = 0
        result_data = []

        if not subjects or not credits or not grades:
             return "<h3 style='color:red;'>Error: No subject data was received. Please ensure subjects were entered.</h3>"

        for i in range(len(subjects)):
            subject = subjects[i]
            credit = int(credits[i])
            grade = grades[i].upper()
            gp = GRADE_POINTS.get(grade, 0)

            total_credits += credit
            weighted_sum += credit * gp

            result_data.append({
                "subject": subject,
                "credit": credit,
                "grade": grade,
                "points": gp
            })
        
        sgpa = round(weighted_sum / total_credits, 2) if total_credits != 0 else 0.0

        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO sgpa_records (name, rollno, department, semester, subject, credit, grade, points, sgpa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        data_to_insert = []
        for item in result_data:
            data_to_insert.append((
                name, rollno, department, semester, 
                item["subject"], item["credit"], item["grade"], item["points"], sgpa
            ))

        cur.executemany(insert_query, data_to_insert) 
        
        conn.commit()
        cur.close()
        conn.close()

        student_info = {
            "name": name,
            "roll": rollno, 
            "department": department,
            "semester": semester
        }

        return render_template('result.html', student=student_info, result=result_data, sgpa=sgpa)

    except Exception as e:
        return f"<h3 style='color:red;'>An unexpected error occurred during calculation or database insertion:</h3><pre>{e}</pre>"


@app.route('/view-records')
def view_records():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        
        # Get all records grouped by student (using GROUP BY instead of DISTINCT with ORDER BY)
        cur.execute("""
            SELECT name, rollno, department, semester, sgpa, MAX(id) as max_id
            FROM sgpa_records
            GROUP BY name, rollno, department, semester, sgpa
            ORDER BY max_id DESC
        """)
        students = cur.fetchall()
        
        # Get detailed records
        cur.execute("""
            SELECT id, name, rollno, department, semester, subject, credit, grade, points, sgpa
            FROM sgpa_records
            ORDER BY id DESC
        """)
        all_records = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('records.html', students=students, all_records=all_records)
    
    except Exception as e:
        return f"<h3 style='color:red;'>Error retrieving records:</h3><pre>{e}</pre>"


if __name__ == '__main__':
    init_db()
    app.run(debug=True)