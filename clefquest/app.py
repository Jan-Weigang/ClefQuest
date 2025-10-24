# ===================================
# ========== System Setup ===========
# ===================================

# Setup system path so docker works well.
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import random

# Flask, SQL and Server stuff
from flask import Flask, render_template, jsonify, request
from flask_sse import sse
from config import Config
from models import *

from routes.student import student_bp
from routes.teacher import teacher_bp
from routes.setup import setup_bp

# ===================================
# ============ Modules ==============
# ===================================

from extensions import db, init_session, redis_client
from auth import init_sso, register_sso_routes

import admin
from utils.encryption import encrypt_answer, decrypt_answer

from decorators.auth import *
from services.musicxml import *

# ===================================
# ============== Setup ==============
# ===================================

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# ===================================
# ==============  DB  ===============
# ===================================

db.init_app(app)

with app.app_context():
    db.create_all()

admin.init_admin(app)           # Sets up the Admin Views for Flask-Admin
init_session(app)               # Sets up flask-session for serverside session storage
init_sso(app)                   # Sets up the IServ SSO from .env
register_sso_routes(app)        # Sets up the SSO Routes


# ===================================
# ============== Redis ==============
# ===================================

import redis
# Check if running in Docker
REDIS_HOST = "redis" if os.getenv("DOCKER_ENV") else "localhost"
app.config["REDIS_URL"] = f"redis://{REDIS_HOST}:6379"
app.config["SSE_REDIS_URL"] = f"redis://{REDIS_HOST}:6379"


try:
    redis_client.ping()  # Test connection
    print(f"✅ Connected to Redis at {REDIS_HOST}:6379")
except redis.ConnectionError:
    print(f"❌ Failed to connect to Redis at {REDIS_HOST}:6379")
    sys.exit()

redis_client.publish("sse", "Hello, Redis!")
# Write to Redis
redis_client.set("test_key", "Redis is working!")

# Read from Redis
value = redis_client.get("test_key")
print(f"✅ Redis Test Value: {value if value else 'No data found'}") # type: ignore

# ======================================================================
# ============================  TODO  ==================================
# ======================================================================


# Umkehrungen

# Behalte die json, benenne um in "notes"
# TODO Musicxml randomisiert momentan noch die Intervalle. 
# Führe das mit den Intervallen 3 mal durch. Gleichzeitig, Arpeggio abwärts, Arpeggio aufwärts.
# Ändere dafür das Model. Arpeggio sollte nicht mehr vorkommen sondern in Data stehen als string NULL, "up", "down"

# TODO Automatische Generierung von Akkorden
# Generiere Major, Minor, Dim, Aug. 
# Das aktuelle Muster sieht Umkehrungen vor im selben Task. Das funktioniert nicht. 
# Also muss die Umkehrung in Data vermerkt werden und jede einzeln generiert werden, um das MusicXML abzuspeichern.

# TODO Timer per Trial


# TODO Check if test is closed in /student
# TODO on closing tests, end all quests



# ======================================================================
# ===========================  Routes  =================================
# ======================================================================

# ======================================================================
# =========================  Blueprints  ===============================
# ======================================================================

app.register_blueprint(sse, url_prefix="/stream")
app.register_blueprint(student_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(setup_bp)

# ======================================================================
# ============================  SSE  ===================================
# ======================================================================

@app.route('/events')
def stream():
    return sse.stream()


@app.route('/sse-test')
def ssetest():
    sse.publish({"message": "Test event"}, type="test")
    return "done"

import time

@app.route('/sse-sub')
def ssesub():
    pubsub = sse.redis.pubsub()
    pubsub.subscribe("sse")

    print("Subscribed to Redis channel 'sse'... Waiting for messages.")

    # Poll for messages for up to 10 seconds
    start_time = time.time()
    while time.time() - start_time < 10:  # Keep checking for 10 seconds
        message = pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            print(f"Received message: {message}")
            return str(message)
        time.sleep(0.1)  # Prevents busy looping

    return "No new messages received in 10 seconds."


# ======================================================================
# =========================  Health-Check  =============================
# ======================================================================

@app.route("/health", methods=["GET"])
def health():
    from sqlalchemy import text, inspect

    status = {"status": "ok", "database": "connected", "redis": "connected"}

    # Check if the DB is accessible and has tables
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()  # List all tables
        if not tables:
            status["database"] = "empty"  # Warn if DB has no tables
        else:
            db.session.execute(text("SELECT 1"))  # Basic DB health check
    except Exception as e:
        status["status"] = "error"
        status["database"] = "unreachable"
        status["db_error"] = str(e)

    # Check Redis
    try:
        redis_client.ping()
    except Exception as e:
        status["status"] = "error"
        status["redis"] = "unreachable"
        status["redis_error"] = str(e)

    # Set HTTP status code based on issues
    http_status = 200 if status["status"] == "ok" else 500
    return jsonify(status), http_status

# ======================================================================
# =========================  Test-Routes  ==============================
# ======================================================================


@app.route("/triadtest")
def triadtest():
    print(generate_triad("C4", "M"))
    print(generate_triad("G#5", "dim"))
    return ""


from music21 import note, interval

def generate_triad(root_note, quality):
    """
    Generate a triad based on a given root note and quality.
    Quality can be: "major", "minor", "diminished", "augmented"
    """
    root = note.Note(root_note)

    # Define intervals based on triad type
    if quality == "M":
        third = interval.Interval("M3")  # Major third
        fifth = interval.Interval("P5")  # Perfect fifth
    elif quality == "m":
        third = interval.Interval("m3")  # Minor third
        fifth = interval.Interval("P5")  # Perfect fifth
    elif quality == "dim":
        third = interval.Interval("m3")  # Minor third
        fifth = interval.Interval("d5")  # Diminished fifth
    elif quality == "aug":
        third = interval.Interval("M3")  # Major third
        fifth = interval.Interval("A5")  # Augmented fifth
    else:
        raise ValueError("Invalid triad quality")

    # Calculate note names
    third_note = third.transposeNote(root)
    fifth_note = fifth.transposeNote(root)

    # Create inversions
    first_inversion = [third_note.nameWithOctave, fifth_note.nameWithOctave, root.transpose("P8").nameWithOctave] # type: ignore
    second_inversion = [fifth_note.nameWithOctave, root.transpose("P8").nameWithOctave, third_note.transpose("P8").nameWithOctave] # type: ignore

    return {
        "root": [root.nameWithOctave, third_note.nameWithOctave, fifth_note.nameWithOctave],
        "first": first_inversion,
        "second": second_inversion
    }


@app.route("/triad")
def triad():

    # Query the database for all triad tasks
    triad_tasks = Task.query.filter_by(type="triads").all()

    # Randomly select one triad task
    selected_task = random.choice(triad_tasks)
    correct_answer = selected_task.display_name

    musicxml = generate_task_musicxml(selected_task)

    # # Generate false answers
    # false_answers = random.sample([t["display_name"] for t in triads["triads"] if t != selected_task], 3)

    # Get false answers using the generalized function
    false_answers = get_false_answers_legacy(
        selected_task=selected_task,
        root_letter_filter=True  # Filter by the first letter of the root
    )

    all_answers = false_answers + [correct_answer]
    # random.shuffle(all_answers)

    encrypted_correct_answer = encrypt_answer(correct_answer)


    return render_template(
        "betatest.html",
        triad={"name": selected_task.name, "musicxml": musicxml},
        answers=all_answers,
        encrypted_answer=encrypted_correct_answer,
    )


@app.route("/reading")
def reading():

    # Query the database for all triad tasks
    reading_tasks = Task.query.filter(
        Task.type == "note-reading",
        Task.root.contains("4")  # Filter by root containing '4'
    ).all()

    # Randomly select one triad task
    selected_task = random.choice(reading_tasks)
    correct_answer = selected_task.display_name

    musicxml = generate_task_musicxml(selected_task)

   # Get false answers using the generalized function
    false_answers = get_false_answers_legacy(
        selected_task=selected_task,
        root_letter_filter=True  # Filter by the first letter of the root
    )
    all_answers = false_answers + [correct_answer]
    random.shuffle(all_answers)

    encrypted_correct_answer = encrypt_answer(correct_answer)


    return render_template(
        "betatest.html",
        triad={"name": selected_task.name, "musicxml": musicxml},
        answers=all_answers,
        encrypted_answer=encrypted_correct_answer,
    )

@app.route("/intervals")
def intervals():

    # Query the database for all triad tasks
    reading_tasks = Task.query.filter(
        Task.type == "intervals",
        Task.root.contains("4"),  # Filter by root containing '4'
    ).all()

    # Randomly select one triad task
    selected_task = random.choice(reading_tasks)
    correct_answer = selected_task.display_name

    musicxml = generate_task_musicxml(selected_task)

   # Get false answers using the generalized function
    false_answers = get_false_answers_legacy(
        selected_task=selected_task,
        root_letter_filter=True  # Filter by the first letter of the root
    )
    all_answers = false_answers + [correct_answer]
    random.shuffle(all_answers)

    encrypted_correct_answer = encrypt_answer(correct_answer)


    return render_template(
        "betatest.html",
        triad={"name": selected_task.name, "musicxml": musicxml},
        answers=all_answers,
        encrypted_answer=encrypted_correct_answer,
    )



@app.route("/check-answer", methods=["POST"])
def check_answer():
    selected_answer = request.form["selected_answer"]
    encrypted_correct_answer = request.form["correct_answer"]

    correct_answer = decrypt_answer(encrypted_correct_answer)

    if selected_answer == correct_answer:
        return jsonify({"result": "Correct!"})
    else:
        return jsonify({"result": "False!"})


# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", threaded=True)
    