from models import *
from extensions import db
from services.musicxml import get_false_answers, get_false_scale_answers
import random, time


from sqlalchemy import and_, or_, text, func

# TODO Moll Dur vs dim
def apply_stage_filters(query, stage, mode_false_answers=False):
    """Applies all filters dynamically to the query based on the stage settings."""

    # tasks = Task.query.filter(Task.name.in_(stage.settings["intervals"])).all() # type: ignore
    # for task in tasks:
    #     print(task.name)
    print("applying stage filters")

    filters = []

    filters.append(Task.clef == stage.clef)
    filters.append(Task.type == stage.task_type)

    # Convert pitch limits to MIDI notes
    lower_limit = pitch.Pitch(stage.lower_limit).midi if stage.lower_limit else None
    upper_limit = pitch.Pitch(stage.upper_limit).midi if stage.upper_limit else None
    if lower_limit and upper_limit:
        filters.append(Task.lowest_midi >= lower_limit)
        filters.append(Task.highest_midi <= upper_limit)

    # Apply JSON-based settings filtering
    if stage.settings:
        settings = stage.settings
        print(f"settings= {settings}")

        if stage.task_type == "intervals":
            # --- Intervals filtering ---
            selected_intervals = settings.get("intervals", [])
            if selected_intervals:
                filters.append(Task.name.in_(selected_intervals))

            # --- Arpeggiation filtering ---
            selected_mode = settings.get("arpeggiated", "random")

            if selected_mode == "arpeggiated":
                # check that the JSON value is NOT NULL → means the key exists
                filters.append(func.json_extract(Task.data, '$.arpeggiated').isnot(None))
            elif selected_mode == "chord":
                # check that the key is missing / NULL
                filters.append(func.json_extract(Task.data, '$.arpeggiated').is_(None))
            
        
        elif stage.task_type == "triads" and "chord_types" in settings:
            filters.append(Task.data["chord_type"].astext.in_(settings["chord_types"]))

        elif stage.task_type == "scales" and "scales" in settings:
            selected_scales = settings["scales"]
            if selected_scales:
                filters.append(or_(*[Task.name.like(f"% {scale}%") for scale in selected_scales]))

        # Accidentals filtering
        accidental_levels = {
            "Keine": 0,
            "Einfache": 1,
            "Doppelte": 2,
            "Komplex": 3
        }
        if not mode_false_answers:
            # Ensure settings exist
            assert "complexity" in settings, "Missing 'complexity' in settings"
            assert "accidentals" in settings, "Missing 'accidentals' in settings"

            max_allowed_complexity = accidental_levels.get(settings["complexity"], 2)
            max_allowed_accidentals = settings["accidentals"]

            filters.append(Task.most_complex_accidental <= max_allowed_complexity)
            filters.append(Task.accidentals <= max_allowed_accidentals)

    # Apply all filters at once
    return query.filter(and_(*filters))






def create_quest(student_id, student_name, test):
    """
    Creates a Completion and associated Trials for a given test.

    Args:
        student_id (str): The unique identifier for the student.
        test (Test): The test object for which the quest is being created.

    Returns:
        Completion: The newly created Completion object.
    """

    start_time = time.perf_counter()

    # Create the quest entry
    quest = Quest(
        test_id=test.id,                    # type: ignore
        student_id=student_id,              # type: ignore
        student_name=student_name             # type: ignore      # Placeholder?
    )
    db.session.add(quest)

    # Flush to generate the ID
    db.session.flush()

    quest_id = quest.id
    print(f"Quest ID {quest_id} has {len(test.stages)} stages")

    # Iterate through test stages instead of task_count
    for stage in test.stages:  # Adjusted to iterate through test stages
        print(f"Processing Test Stage: {stage}")

        # Get filtered tasks
        query = Task.query

        query = apply_stage_filters(query, stage)
        filtered_tasks = query.all()

        print(f"Filter: {stage.task_type}, Tasks Available: {len(filtered_tasks)}")

        # Randomly sample tasks
        if len(filtered_tasks) >= stage.count:
            selected_tasks = random.sample(filtered_tasks, stage.count)
        else:
            selected_tasks = filtered_tasks  # Use all tasks if not enough are available



        false_query = Task.query
        false_query = apply_stage_filters(false_query, stage, mode_false_answers=True)
        filtered_false_tasks = false_query.all()

        

        for task in selected_tasks:

            match task.type:

                case "note-reading":
                    false_answers = get_false_answers(task, filtered_tasks, root_letter_filter=False)

                case "intervals":
                    false_answers = get_false_answers(task, filtered_false_tasks)       # type: ignore

                case "scales":
                    false_answers = get_false_answers(task, filtered_false_tasks)       # type: ignore
            
                case "triads":
                    false_answers = get_false_answers(task, filtered_false_tasks)       # type: ignore
            
                case _:
                    false_answers = []
                    print("Reached impossible Task during create quest")


            correct_answer = task.display_name
            possible_answers = false_answers + [correct_answer]
            random.shuffle(possible_answers)

            trial = Trial(
                quest_id=quest_id,                      # type: ignore
                task_id=task.id,                        # type: ignore
                correct_answer=correct_answer,          # type: ignore
                possible_answers=possible_answers,      # type: ignore
                stage_id=stage.id                       # type: ignore
            )
            print(trial)
            db.session.add(trial)

    db.session.commit()    
    total_time = time.perf_counter() - start_time
    print(f"Total create_quest() execution time: {total_time:.6f} seconds")
    return quest

