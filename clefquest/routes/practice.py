from flask import Blueprint, render_template, request, session, redirect, url_for, abort
from decorators.auth import is_teacher
from models import *

# IMPORT CREATE QUEST
from services.quest_generator import create_quest
from assets import piano_svg

import json
from extensions import redis_client  # your configured Redis instance

practice_bp = Blueprint('practice', __name__, url_prefix='/practice')






@practice_bp.route('/plenum/start/<string:test_id>', methods=['GET', 'POST'])
def plenum_start(test_id):
    """Prepare and configure plenum mode before launching."""
    test = Test.query.get_or_404(test_id)

    user_info = session.get("user_info", {})
    user_roles = user_info.get("roles", [])
    user_is_student = any(role.get("id") == "ROLE_STUDENT" for role in user_roles)
    user_is_teacher = any(role.get("id") == "ROLE_TEACHER" for role in user_roles)

    if user_is_student and not test.is_practicable:
        abort(403, "This test is not available for practice")


    if user_is_student:
        redis_key = f"plenum:{test_id}:{session['user_info']['preferred_username']}"
    else:
        redis_key = f"plenum:{test_id}:teacher"

    if request.method == "POST":
        # Always create a fresh quest
        if user_is_student:
            student_id = session["user_info"]["preferred_username"]
            student_name = session["user_info"]["name"]
            quest = create_quest(student_id, student_name, test)
        else:
            quest = create_quest("plenum_mode", "Übungstest", test)
        countdown = int(request.form.get("countdown", 20))

        plenum = {
            "index": 0,
            "show_solution": False,
            "countdown": countdown,
            "quest": {
                "id": quest.id,
                "trials": [
                    {
                        "id": t.id,
                        "task_type": t.task.type,
                        "musicxml": t.task.musicxml,
                        "correct_answer": t.correct_answer,
                        "possible_answers": t.possible_answers,
                        "display_name": t.task.display_name,
                    }
                    for t in quest.tasks
                ],
            },
        }

        redis_client.set(redis_key, json.dumps(plenum), ex=3600)
        return redirect(url_for('practice.plenum_mode', test_id=test.id))

    return render_template('plenum_start.html', test=test)






@practice_bp.route('/plenum/<string:test_id>', methods=['GET', 'POST'])
def plenum_mode(test_id):
    """Run test in plenum mode with Redis-backed quest state."""
    test = Test.query.get_or_404(test_id)

    user_info = session.get("user_info", {})
    user_roles = user_info.get("roles", [])
    user_is_student = any(role.get("id") == "ROLE_STUDENT" for role in user_roles)
    user_is_teacher = any(role.get("id") == "ROLE_TEACHER" for role in user_roles)

    if user_is_student and not test.is_practicable:
        abort(403, "This test is not available for practice")

    if user_is_student:
        redis_key = f"plenum:{test_id}:{session['user_info']['preferred_username']}"
    else:
        redis_key = f"plenum:{test_id}:teacher"


    # Try to load plenum quest from Redis
    plenum_data = redis_client.get(redis_key)
    if plenum_data:
        plenum = json.loads(plenum_data)
    else:
        return "no plenum test found."
    

    trials = plenum["quest"]["trials"]
    total_tasks = len(trials)
    idx = plenum["index"]

    if request.method == "POST":
        action = request.form.get("action")
        if action != "next":
            return "wrong action"
        
        plenum["index"] += 1
        
        if plenum["index"] >= total_tasks - 1:
            redis_client.delete(redis_key)
            print("deleting")
            if user_is_student:
                print("user is student")
                student_id = session["user_info"]["preferred_username"]
                student_name = session["user_info"]["name"]
                db.session.add(PracticeCompletion(student_id=student_id, student_name=student_name, test_id=test.id))
                db.session.commit()
            return render_template(
                "plenum_completed.html", 
                test=test,
                trials=trials,
                total_tasks=total_tasks
            )
            
        redis_client.set(redis_key, json.dumps(plenum), ex=3600)
        return redirect(url_for('practice.plenum_mode', test_id=test_id))

    if idx >= total_tasks:
        redis_client.delete(redis_key)
        if user_is_student:
            student_id = session["user_info"]["preferred_username"]
            student_name = session["user_info"]["name"]
            db.session.add(PracticeCompletion(student_id=student_id, student_name=student_name, test_id=test.id))
            db.session.commit()
        return render_template(
            "plenum_completed.html", 
            test=test,
            trials=trials,
            total_tasks=total_tasks
        )

    next_trial = trials[idx]
    progress = round((idx / total_tasks) * 100, 2)
    countdown = plenum.get("countdown", 10)

    return render_template(
        "student/quest/trial.html",
        task_type=next_trial["task_type"],
        trial_id=next_trial["id"],
        answers=next_trial["possible_answers"],
        progress=progress,
        musicxml=next_trial["musicxml"],
        piano_svg=piano_svg,
        is_plenum=True,
        countdown=countdown
    )
