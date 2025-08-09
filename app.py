from flask import Flask, render_template, request, send_from_directory
from pymysql import connections
import os
import random
import argparse
import boto3
from botocore.exceptions import ClientError
import logging
import tempfile


app = Flask(__name__)

# Configure logging
app.logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)


# Get environment variables

DBHOST = os.environ.get("DBHOST") or "localhost"
DBUSER = os.environ.get("DBUSER") or "root"
DBPWD = os.environ.get("DBPWD") or "password"
DATABASE = os.environ.get("DATABASE") or "employees"
COLOR_FROM_ENV = os.environ.get('APP_COLOR') or "lime"

DBPORT = int(os.environ.get("DBPORT", 3306))
STUDENT_NAME = os.environ.get("STUDENT_NAME", "Student")




BG_IMAGE_URL = os.environ.get("BG_IMAGE_URL", "")

# Log background image URL
app.logger.info(f"Background image URL: {BG_IMAGE_URL}")


# Download background image from S3
def download_background_image():
    if not BG_IMAGE_URL or not BG_IMAGE_URL.startswith("s3://"):
        app.logger.warning("Invalid or missing BG_IMAGE_URL")
        return
    
    try:
        # Parse S3 URL (s3://bucket-name/key)
        s3_path = BG_IMAGE_URL[5:]
        bucket_name, key = s3_path.split("/", 1)
        
        # Initialize S3 client
        s3 = boto3.client('s3')
        
        # Download image to static folder
        static_dir = os.path.join(app.root_path, 'static')
        os.makedirs(static_dir, exist_ok=True)
        local_path = os.path.join(static_dir, 'background.jpg')
        
        s3.download_file(bucket_name, key, local_path)
        app.logger.info(f"Successfully downloaded background image to {local_path}")
        
    except ClientError as e:
        app.logger.error(f"S3 download error: {e}")
    except Exception as e:
        app.logger.error(f"Error downloading image: {e}")

# Download image on app startup
download_background_image()


# Create a connection to the MySQL database
db_conn = connections.Connection(
    host=DBHOST,
    port=DBPORT,
    user=DBUSER,
    password=DBPWD, 
    db=DATABASE
)
output = {}
table = 'employee'

# Define the supported color codes
color_codes = {
    "red": "#e74c3c",
    "green": "#16a085",
    "blue": "#89CFF0",
    "blue2": "#30336b",
    "pink": "#f4c2c2",
    "darkblue": "#130f40",
    "lime": "#C1FF9C",
}

# Generate a random color
COLOR = random.choice(list(color_codes.keys()))

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('addemp.html', color=color_codes[COLOR], student_name=STUDENT_NAME)

@app.route("/about", methods=['GET','POST'])
def about():
    return render_template('about.html', color=color_codes[COLOR], student_name=STUDENT_NAME)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = f"{first_name} {last_name}"
    finally:
        cursor.close()

    return render_template('addempoutput.html', name=emp_name, color=color_codes[COLOR], student_name=STUDENT_NAME)

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    return render_template("getemp.html", color=color_codes[COLOR], student_name=STUDENT_NAME)

@app.route("/fetchdata", methods=['GET','POST'])
def FetchData():
    emp_id = request.form['emp_id']
    output = {}
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location from employee where emp_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (emp_id,))
        result = cursor.fetchone()
        
        if result:
            output["emp_id"] = result[0]
            output["first_name"] = result[1]
            output["last_name"] = result[2]
            output["primary_skills"] = result[3]
            output["location"] = result[4]
        else:
            return render_template("getempoutput.html", error="Employee not found", color=color_codes[COLOR], student_name=STUDENT_NAME)
    except Exception as e:
        app.logger.error(f"Database error: {e}")
        return render_template("getempoutput.html", error="Database error", color=color_codes[COLOR], student_name=STUDENT_NAME)
    finally:
        cursor.close()

    return render_template("getempoutput.html", 
                           id=output["emp_id"], 
                           fname=output["first_name"],
                           lname=output["last_name"], 
                           interest=output["primary_skills"], 
                           location=output["location"], 
                           color=color_codes[COLOR],
                           student_name=STUDENT_NAME)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

if __name__ == '__main__':
    # Check for Command Line Parameters for color
    parser = argparse.ArgumentParser()
    parser.add_argument('--color', required=False)
    args = parser.parse_args()

    if args.color:
        app.logger.info(f"Color from command line argument: {args.color}")
        COLOR = args.color
        if COLOR_FROM_ENV:
            app.logger.info(f"Color from environment variable ({COLOR_FROM_ENV}) overridden by command line")
    elif COLOR_FROM_ENV:
        app.logger.info(f"Using color from environment variable: {COLOR_FROM_ENV}")
        COLOR = COLOR_FROM_ENV
    else:
        app.logger.info(f"No color specified, using random color: {COLOR}")

    # Check if input color is supported
    if COLOR not in color_codes:
        app.logger.error(f"Unsupported color '{COLOR}'. Supported: {list(color_codes.keys())}")
        exit(1)

    app.run(host='0.0.0.0', port=81, debug=True)