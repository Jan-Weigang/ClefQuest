from flask import Blueprint, render_template, request, session, redirect, url_for
from decorators.auth import is_teacher
from models import *

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

# =======================  Apply the Decorator to the Whole Blueprint =============================

# Flask does not have a built-in way to apply a decorator to all routes in a blueprint.
# However, we can use `before_request` to enforce a decorator like `@is_student`.

@teacher_bp.before_request
@is_teacher
def check_teacher():
    """Applies the `is_student` decorator to all routes in the blueprint."""
    pass  # This ensures that any request made to /student/* is checked by is_student

# =======================  Routes =============================


@teacher_bp.route('/', methods=['GET'])
@is_teacher
def teacher_dashboard():
    """
    Teacher dashboard with links to groups and tests management.
    """
    return render_template('teacher/dashboard.html')



# @teacher_bp.route('/group/<string:group_id>', methods=['GET'])
# @is_teacher
# def teacher_group_details(group_id):
#     """
#     Displays a table of all students in a group with their quests and overall percentages.
#     """
#     try:
#         # Fetch the group
#         group = Group.query.get_or_404(group_id)

#         # Fetch all tests in the group
#         tests = Test.query.filter_by(group_id=group.id).all()
#         test_ids = [test.id for test in tests]

#         # Fetch all quests for the group's tests
#         quests = Quest.query.filter(Quest.test_id.in_(test_ids)).all()

#         # Organize data by student
#         student_data = {}
#         for quest in quests:
#             student_id = quest.student_id
#             if student_id not in student_data:
#                 student_data[student_id] = {
#                     "student_name": quest.student_name,
#                     "quests": [],
#                     "total_tasks": 0,
#                     "correct_tasks": 0
#                 }
#             # Add quest details
#             student_data[student_id]["quests"].append(quest)

#             # Calculate total and correct tasks
#             for task in quest.tasks:
#                 student_data[student_id]["total_tasks"] += 1
#                 if task.is_correct:
#                     student_data[student_id]["correct_tasks"] += 1

#         # Calculate overall percentages
#         for student in student_data.values():
#             if student["total_tasks"] > 0:
#                 student["percentage"] = round(
#                     (student["correct_tasks"] / student["total_tasks"]) * 100, 2
#                 )
#             else:
#                 student["percentage"] = 0.0

#         return render_template(
#             'teacher/group_details.html',
#             group=group,
#             student_data=student_data
#         )

#     except Exception as e:
#         db.session.rollback()
#         print(f"Error: {str(e)}")
#         return render_template("error.html", error_message=str(e)), 500




@teacher_bp.route('/groups', methods=['GET', 'POST'])
@is_teacher
def teacher_groups():
    teacher_id = session["user_info"].get("sub")

    if request.method == 'GET':
        # Extract groups from session
        raw_groups = session["user_info"].get("groups", {})

        # Transform groups
        sso_groups = [
            {"act": group_data["act"], "name": group_data["name"]}
            for group_data in raw_groups.values()
        ]

        # Check database for existing groups
        db_groups = Group.query.filter(
            Group.teacher_id == teacher_id, 
            Group.name.in_([g["act"] for g in sso_groups])
        ).all()
        existing_groups = {group.name for group in db_groups}

        return render_template('teacher/groups.html', sso_groups=sso_groups, existing_groups=existing_groups)

    elif request.method == 'POST':
        # Activate groups based on user input
        group_acts = request.form.getlist('group_acts')  # List of "act" values
        for group_act in group_acts:
            group = Group.query.filter_by(name=group_act).first()
            if not group:
                group = Group(name=group_act, teacher_id=teacher_id, students=[]) # type: ignore
                db.session.add(group)

        db.session.commit()
        return redirect(url_for('teacher.teacher_groups'))
    
    else:
        return redirect("/")


@teacher_bp.route('/tests', methods=['GET', 'POST'])
@is_teacher
def teacher_tests():
    try:
        teacher_id = session["user_info"].get("sub")

        # Extract groups from session
        raw_groups = session["user_info"].get("groups", {})
        sso_groups = [
            {"act": group_data["act"], "name": group_data["name"]}
            for group_data in raw_groups.values()
        ]

        # Fetch groups associated with the teacher
        db_groups = Group.query.filter(
            Group.teacher_id == teacher_id, 
            Group.name.in_([g["act"] for g in sso_groups])
        ).all()
        group_ids = [group.id for group in db_groups]

        # Fetch tests belonging to the teacher's groups
        tests = Test.query.filter(Test.group_id.in_(group_ids)).all()

        if request.method == 'POST':
            # Close selected tests
            test_ids_to_close = request.form.getlist('test_ids')
            for test_id in test_ids_to_close:
                test = Test.query.get(test_id)
                if test and test.group_id in group_ids:  # Ensure the test belongs to a group the teacher owns
                    test.open = False
            db.session.commit()
            return redirect(url_for('teacher.teacher_tests'))

        return render_template('teacher/tests.html', tests=tests)

    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return render_template("error.html", error_message=str(e)), 500



@teacher_bp.route("/teacher/test/<test_id>")
@is_teacher
def teacher_test_details(test_id):
    test = Test.query.get_or_404(test_id)
    quests = Quest.query.filter_by(test_id=test_id).all()

    student_data = {}
    for quest in quests:
        sid = quest.student_id
        if sid not in student_data:
            student_data[sid] = {
                "student_name": quest.student_name,
                "quests": [],
                "total_tasks": 0,
                "correct_tasks": 0,
            }

        student_data[sid]["quests"].append(quest)
        for trial in quest.tasks:
            student_data[sid]["total_tasks"] += 1
            if trial.is_correct:
                student_data[sid]["correct_tasks"] += 1

    for student in student_data.values():
        student["percentage"] = round(
            (student["correct_tasks"] / student["total_tasks"]) * 100, 2
        ) if student["total_tasks"] > 0 else 0.0

    return render_template("teacher/test_details.html", test=test, student_data=student_data)



from collections import defaultdict

@teacher_bp.route("/teacher/group/<group_id>")
@is_teacher
def teacher_group_details(group_id):
    group = Group.query.get_or_404(group_id)
    tests = Test.query.filter_by(group_id=group_id).all()
    quests = Quest.query.join(Test).filter(Test.group_id == group_id).all()

    student_map = {}
    for quest in quests:
        sid = quest.student_id
        tid = quest.test_id
        if sid not in student_map:
            student_map[sid] = {
                "student_name": quest.student_name,
                "results": {t.id: defaultdict(lambda: {"correct": 0, "total": 0}) for t in tests}
            }

        for trial in quest.tasks:
            stage_id = trial.stage_id
            correct = 1 if trial.is_correct else 0
            student_map[sid]["results"][tid][stage_id]["correct"] += correct
            student_map[sid]["results"][tid][stage_id]["total"] += 1

    # Convert result dict to a list of %s in the order of test.stages
    for sid, student in student_map.items():
        for test in tests:
            stage_results = []
            for stage in test.stages:
                stats = student["results"][test.id][stage.id]
                total = stats["total"]
                percent = (stats["correct"] / total * 100) if total else 0
                stage_results.append(round(percent, 2))
            student["results"][test.id] = stage_results

    stage_count = {test.id: len(test.stages) for test in tests}
    test_stages = {test.id: test.stages for test in tests}

    stage_trial_count = defaultdict(int)
    for quest in quests:
        for trial in quest.tasks:
            stage_trial_count[trial.stage_id] += 1


    return render_template(
        "teacher/group_details.html",
        group=group,
        tests=tests,
        students=student_map,
        stage_count=stage_count,
        test_stages=test_stages,
        stage_trial_count=stage_trial_count
    )





# TODO THIS MUST BE ADJUSTED for new models and also the forms
@teacher_bp.route('/test/create', methods=['GET', 'POST'])
@is_teacher
def teacher_test_create():
    try:
        # Extract groups from session
        raw_groups = session["user_info"].get("groups", {})
        sso_groups = [
            {"act": group_data["act"], "name": group_data["name"]}
            for group_data in raw_groups.values()
        ]

        # Fetch existing groups in the database
        db_groups = Group.query.filter(Group.name.in_([g["act"] for g in sso_groups])).all()

        if request.method == 'GET':
            return render_template('teacher/create_test.html', groups=db_groups)

        elif request.method == 'POST':
            print(request)
            # Retrieve form data
            title = request.form['title']
            description = request.form['description']
            group_id = request.form['group_id']  # Selected group
            
            # Extract test stages from form data # TODO Make into function
            stages = []
            index = 0
            while f'stage[{index}][task_type]' in request.form:
                stage_data = {
                    "task_type": request.form.get(f'stage[{index}][task_type]'),
                    "count": int(request.form.get(f'stage[{index}][count]', 0)),
                    # "difficulty": int(request.form.get(f'stage[{index}][difficulty]', 0)),
                    "clef": request.form.get(f'stage[{index}][clef]'),
                    "lower_limit": request.form.get(f'stage[{index}][lower_limit]'),
                    "upper_limit": request.form.get(f'stage[{index}][upper_limit]'),
                    "settings": {               # Store additional settings in JSON
                        "complexity": request.form.get(f'stage[{index}][complexity]', None),
                        "accidentals": request.form.get(f'stage[{index}][accidentals]', None),
                        "arpeggiated": request.form.get(f'stage[{index}][arpeggiated]', None),
                        "intervals": request.form.getlist(f'stage[{index}][intervals][]'),
                        "scales": request.form.getlist(f'stage[{index}][scales][]'),
                    }
                }
                print(f"stage data is: {stage_data}")
                stages.append(stage_data)
                index += 1

            print(f"Extracted stages: {stages}")

            # Validate group
            group = Group.query.get_or_404(group_id)

            # Create a new test
            new_test = Test(
                title=title,                # type: ignore
                description=description,    # type: ignore
                group_id=group.id,          # type: ignore
                open=True  # Default to open # type: ignore
            )
            db.session.add(new_test)
            db.session.commit()
            print("added new test")

            # Create test stages
            for stage in stages:
                task_type = stage.get('task_type')
                count = int(stage.get('count', 0))
                clef = stage.get('clef')
                lower_limit = stage.get('lower_limit')
                upper_limit = stage.get('upper_limit')
                settings = stage.get("settings", {})

                new_stage = Stage(
                    test_id=new_test.id,                # type: ignore
                    task_type=task_type,                # type: ignore
                    count=count,                        # type: ignore
                    clef=clef,                          # type: ignore
                    lower_limit=lower_limit,            # type: ignore
                    upper_limit=upper_limit,            # type: ignore
                    settings=settings,                  # type: ignore
                )
                db.session.add(new_stage)
                print(f"Added stage: {new_stage}")

            db.session.commit()

            return redirect(url_for('teacher.teacher_tests'))  # Redirect to a dashboard or main teacher page
        
        else:
            return redirect("/")

    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return render_template("error.html", error_message=str(e)), 500

