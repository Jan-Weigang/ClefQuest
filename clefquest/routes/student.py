from flask import Blueprint, render_template, request, session, jsonify
from models import *
from utils.encryption import encrypt_answer, decrypt_answer
from decorators.auth import is_student  # Ensure this works on a Blueprint

# IMPORT CREATE QUEST
from services.quest_generator import create_quest

student_bp = Blueprint('student', __name__, url_prefix='/student')

# =======================  Apply the Decorator to the Whole Blueprint =============================

# Flask does not have a built-in way to apply a decorator to all routes in a blueprint.
# However, we can use `before_request` to enforce a decorator like `@is_student`.

@student_bp.before_request
@is_student
def check_student():
    """Applies the `is_student` decorator to all routes in the blueprint."""
    pass  # This ensures that any request made to /student/* is checked by is_student

# =======================  Routes =============================

@student_bp.route('/', methods=['GET'])
def student():
    """Lists available tests for the student's groups."""
    raw_groups = session["user_info"].get("groups", {})
    sso_groups = [{"act": group_data["act"], "name": group_data["name"]} for group_data in raw_groups.values()]
    
    db_groups = Group.query.filter(Group.name.in_([g["act"] for g in sso_groups])).all()

    groups_with_tests = [
        {"group_name": group.name, "tests": [{"id": test.id, "title": test.title} for test in Test.query.filter_by(group_id=group.id, open=True).all()]}
        for group in db_groups
    ]

    return render_template('student/groups.html', groups=groups_with_tests)


@student_bp.route('/tests/<string:test_id>', methods=['GET', 'POST'])
def student_test(test_id):
    """Handles test access and submissions."""
    try:
        # print("Session user info:", session.get("user_info", {}))

        # Extract student information
        raw_groups = session["user_info"].get("groups", {})
        sso_groups = [group_data["act"] for group_data in raw_groups.values()]
        
        test = Test.query.get_or_404(test_id)
        print("Retrieved test:", test)

        if test.group.name not in sso_groups:
            return render_template("error.html", error_message="You do not have access to this test."), 403

        student_id = session["user_info"]["preferred_username"]
        print("Student ID:", student_id)
        quest = Quest.query.filter_by(test_id=test.id, student_id=student_id).first() or create_quest(student_id, test)
        print("Quest:", quest)

        # ============================
        # =========== POST ===========
        # ============================

        if request.method == 'POST':
            # Handle answer submission
            selected_answer = request.form["selected_answer"]
            encrypted_correct_answer = request.form["correct_answer"]
            trial_id = request.form["trial_id"]
            correct_answer = decrypt_answer(encrypted_correct_answer)

            # Find the specific Trial being answered
            current_task = Trial.query.get(trial_id)
            if not current_task:
                return jsonify({"result": "Invalid task."}), 400

            # Save the given answer if not already submitted
            if current_task.given_answer is None:
                current_task.given_answer = selected_answer
                current_task.is_correct = (selected_answer == correct_answer)
                db.session.commit()

            return render_template("student/quest/result.html", 
                                   is_correct=current_task.is_correct,
                                   correct_answer=correct_answer)

        # ============================
        # =========== GET ============
        # ============================

        if not test.open:
            return "Dieser Test wurde beendet."

        # Get all tasks in this quest
        assigned_tasks = list(quest.tasks) # type: ignore

        # Filter for tasks without a given answer (i.e., unanswered tasks)
        unanswered_tasks = [task for task in assigned_tasks if task.given_answer is None]

        if not unanswered_tasks:
            trials = Trial.query.filter_by(quest_id=quest.id).all()
            total_tasks = len(trials)
            correct_percentage = round((sum(1 for task in trials if task.is_correct) / total_tasks) * 100, 2)

            return render_template("student/quest/completed.html", 
                                   total_tasks=total_tasks, 
                                   trials=trials, 
                                   correct_percentage=correct_percentage)

        # Pick the next unanswered task
        next_task = unanswered_tasks[0]

        # Calculate progress
        total_tasks = len(assigned_tasks)
        progress = round(((total_tasks - len(unanswered_tasks)) / total_tasks) * 100, 2)

        # piano_svg = generate_piano_svg()

        return render_template(
            "student/quest/trial.html",
            task_type=next_task.task.type,
            trial_id=next_task.id,
            answers=next_task.possible_answers,
            progress=progress,
            musicxml=next_task.task.musicxml,
            encrypted_answer=encrypt_answer(next_task.correct_answer),
            piano_svg=piano_svg
        )

    except Exception as e:
        db.session.rollback()
        return render_template("error.html", error_message=str(e)), 500



def generate_piano_svg():
    """Generates an SVG of a piano keyboard from lowest_midi to highest_midi, marking all 'C' keys."""
    lowest_midi = 48
    highest_midi = 72
    width = 500
    height = 80


    key_width = width / 15  # Auto-scale keys
    white_keys = [0, 2, 4, 5, 7, 9, 11]  # MIDI offsets for white keys
    black_keys = [1, 3, 6, 8, 10]        # MIDI offsets for black keys
    key_height = height
    black_key_height = height * 0.6
    black_key_width = key_width * 0.7

    # SVG Start
    svg = f'<svg width="{width}" height="auto" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: min(100%,500px);">\n'

    # Draw white keys
    x_pos = 0
    midi_to_x = {}  # Map MIDI notes to x positions
    for midi in range(lowest_midi, highest_midi + 1):
        note = midi % 12
        if note in white_keys:
            svg += f'<rect x="{x_pos}" y="0" width="{key_width}" height="{key_height}" fill="white" stroke="black" stroke-width="1.5"/>\n'
            midi_to_x[midi] = x_pos
            x_pos += key_width

    # Draw black keys (overlayed)
    for midi in range(lowest_midi, highest_midi + 1):
        note = midi % 12
        if note in black_keys:
            x_black = midi_to_x.get(midi - 1, 0) + (key_width - black_key_width / 2)
            svg += f'<rect x="{x_black}" y="0" width="{black_key_width}" height="{black_key_height}" fill="black" stroke="black"/>\n'

    svg += '</svg>'
    return svg


piano_svg = """
<svg width="500" height="auto" viewBox="0 0 500 80" xmlns="http://www.w3.org/2000/svg" style="width: min(100%,500px);">
<rect x="0" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="33.333333333333336" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="66.66666666666667" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="100.0" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="133.33333333333334" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="166.66666666666669" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="200.00000000000003" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="233.33333333333337" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="266.6666666666667" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="300.0" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="333.3333333333333" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="366.66666666666663" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="399.99999999999994" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="433.33333333333326" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="466.6666666666666" y="0" width="33.333333333333336" height="80" fill="white" stroke="black" stroke-width="1.5"></rect>
<rect x="21.66666666666667" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="55.00000000000001" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="121.66666666666667" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="155.0" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="188.33333333333337" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="255.00000000000006" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="288.33333333333337" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="355.0" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="388.3333333333333" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
<rect x="421.66666666666663" y="0" width="23.333333333333332" height="48.0" fill="black" stroke="black"></rect>
</svg>"""