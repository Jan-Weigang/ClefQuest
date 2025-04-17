from flask import Blueprint, render_template, current_app
from flask_sse import sse
from decorators.auth import is_teacher
from models import *
import utils
from music21 import note, interval, chord, scale

from threading import Thread

setup_bp = Blueprint('setup', __name__, url_prefix='/setup')

# =======================  Apply the Decorator to the Whole Blueprint =============================

# Flask does not have a built-in way to apply a decorator to all routes in a blueprint.
# However, we can use `before_request` to enforce a decorator like `@is_student`.

@setup_bp.before_request
@is_teacher
def check_teacher():
    """Applies the `is_student` decorator to all routes in the blueprint."""
    pass  # This ensures that any request made to /student/* is checked by is_student

# =======================  Routes =============================

# TODO Make this more robust so it will not get done multiple times at the same time

@setup_bp.route('/reloadTasks', methods=['GET'])
def reload_tasks():
    """Start task reload in the background and return immediately."""
    app = current_app._get_current_object() # type: ignore
    thread = Thread(target=process_tasks, args=(app,), daemon=True)
    thread.start()
    
    # Render an HTMX-friendly response
    return render_template("setup/reload_tasks.html")  # Show live progress


def process_tasks(app):
    """Processes tasks and updates the frontend in real-time."""
    try:
        with app.app_context():
            # Clear existing tasks
            Task.query.delete()
            db.session.commit()
            sse.publish({"message": "Cleared existing tasks."}, type="update")

            tasks_data = utils.load_json("notes.json")
            german_intervals = utils.load_yaml("german_intervals.yaml")
            interval_data = german_intervals["intervals"]

            # calculate total tasks
            amount_note_reading = len(tasks_data.get("note-reading", []))
            amount_intervals = len(interval_data) * amount_note_reading * 3
            amount_triads = amount_note_reading * 4 * 3
            amount_scales = amount_note_reading * 9
            total_tasks = (amount_note_reading + amount_intervals + amount_triads + amount_scales) * 6

            processed_tasks = 0
            print("Starting task processing...")

            notes_data = tasks_data.get("note-reading", [])

            clefs = ["treble", "bass", "alto", "percussion", "treble-8", "treble+8"]

            for clef in clefs:
                processed_tasks = create_note_reading_tasks(notes_data, clef, processed_tasks, total_tasks)
                sse.publish({"message": f"{amount_note_reading} Note-Reading-Aufgaben hinzugefügt"}, type="milestone")
                
                processed_tasks = create_interval_tasks(notes_data, clef, interval_data, processed_tasks, total_tasks)
                sse.publish({"message": f"{amount_intervals} Intervall-Aufgaben hinzugefügt"}, type="milestone")

                processed_tasks = create_triad_tasks(notes_data, clef, processed_tasks, total_tasks)
                sse.publish({"message": f"{amount_triads} Dreiklang-Aufgaben hinzugefügt"}, type="milestone")

                processed_tasks = create_scale_tasks(notes_data, clef, processed_tasks, total_tasks)
                sse.publish({"message": f"{amount_scales} Tonleiter-Aufgaben hinzugefügt"}, type="milestone")
        
            print("Finished Processing")
            sse.publish({"message": "Fertig!"}, type="update")
            sse.publish({"message": "Fertig!"}, type="milestone")

            import time
            time.sleep(1)

    except Exception as e:
        print(e)
        from flask import current_app as app
        with app.app_context():
            db.session.rollback()
            sse.publish({"error": str(e)}, type="error")



def create_note_reading_tasks(notes_data, clef, counter, total):
    # Process Note-Reading Tasks
    tasks = []
    for template in notes_data:
        task = Task(
            type="note-reading",
            display_name=template["display_name"],
            name=template["note"],
            root=template["note"],
            clef=clef
        )
        tasks.append(task)
        counter += 1

    db.session.bulk_save_objects(tasks)
    db.session.commit()
    sse.publish({"progress": counter, "total": total, "message": f"Clef: {clef} Note-Reading:"}, type="update")
    
    print("Finished Note-Reading Tasks")
    return counter

def create_interval_tasks(notes_data, clef, interval_data, counter, total):
    # Process Interval Tasks
    for root_note_template in notes_data:                               # For every note
        root_note = root_note_template["note"]
        tasks = []
        for interval_name, german_name in interval_data.items():        # For every Interval
            try:
                root = note.Note(root_note)
                interval_obj = interval.Interval(interval_name)
                target_note = interval_obj.transposeNote(root)

                for arpeggiated in ["up", "down", None]:                # For all versions (arpeggiated and not)

                    task_data = {"notes": [root.nameWithOctave, target_note.nameWithOctave]}

                    if arpeggiated:  # Only add 'arpeggiated' key if it's not None
                        task_data["arpeggiated"] = arpeggiated

                    task = Task(
                        type="intervals",
                        name=interval_name,
                        display_name=german_name,
                        root=root_note,
                        clef=clef,
                        data=task_data
                    )
                    tasks.append(task)
                    counter += 1
                

            except Exception as e:
                print(f"Error creating interval task: {e}")

        db.session.bulk_save_objects(tasks)
        sse.publish({"progress": counter, "total": total, "message": f"Intervalle ({root_note})"}, type="update")

    db.session.commit()
    print("Finished Interval Tasks")
    return counter

def create_triad_tasks(notes_data, clef, counter, total):
    # Mapping inversions to German names
    inversion_map = {
        0: "",
        1: "(1. Umk)",
        2: "(2. Umk)"
    }

    # Mapping triad qualities to German names
    quality_map = {
        "major": "",
        "minor": "m",
        "diminished": "°",
        "augmented": "+"
    }

    # Process Triad Tasks
    for root_note_template in notes_data:  # For every note
        root_note = root_note_template["note"]
        root_display = pitch.Pitch(root_note).name.replace("-", "b")
        tasks = []

        for quality in ["major", "minor", "diminished", "augmented"]:  # For each quality
            try:
                for inversion in [0, 1, 2]:
                    triad_data = generate_triad(root_note, quality, inversion)

                    task = Task(
                        type="triads",
                        name=f"{root_note} {quality} {inversion}",
                        display_name=f"{root_display}{quality_map[quality]} {inversion_map[inversion]}",
                        root=root_note,
                        clef=clef,
                        data={
                            "notes": [p.nameWithOctave for p in triad_data.pitches],  # Extract pitch names
                            "inversion": inversion
                        },
                    )

                    tasks.append(task)
                    counter += 1

            except Exception as e:
                print(f"Error creating triad task ({root_note}, {quality}, {inversion_map[inversion]}): {e}") # type: ignore

        # Update progress after each root note
        db.session.bulk_save_objects(tasks)
        sse.publish({"progress": counter, "total": total, "message": f"Dreiklänge ({root_note})"}, type="update")
        db.session.commit()

    print("Finished Triad Tasks")
    return counter

def generate_triad(root_note, quality, inversion=0):
    """
    Generate a triad based on a given root note and quality using music21's chord.Chord.
    Supports inversions 0 (root), 1 (first inversion), and 2 (second inversion).
    """
    triad_map = {
        "major": ["M3", "P5"],  # Major third, Perfect fifth
        "minor": ["m3", "P5"],  # Minor third, Perfect fifth
        "diminished": ["m3", "d5"],  # Minor third, Diminished fifth
        "augmented": ["M3", "A5"]  # Major third, Augmented fifth
    }

    if quality not in triad_map:
        raise ValueError(f"Invalid triad quality: {quality}")

    root = note.Note(root_note)
    third = root.transpose(interval.Interval(triad_map[quality][0]))  # Third interval
    fifth = root.transpose(interval.Interval(triad_map[quality][1]))  # Fifth interval

    triad = chord.Chord([root, third, fifth]) # type: ignore
    triad.inversion(inversion)  # Apply inversion

    return triad  # Correctly returns a music21.chord.Chord object



def create_scale_tasks(notes_data, clef, counter, total):
    SCALE_NAME_MAP = {
        scale.MajorScale: "Dur",
        scale.MinorScale: "Moll",
        scale.MelodicMinorScale: "Melodisch Moll",
        scale.HarmonicMinorScale: "Harmonisch Moll",
        scale.DorianScale: "Dorisch",
        scale.PhrygianScale: "Phrygisch",
        scale.LydianScale: "Lydisch",
        scale.MixolydianScale: "Mixolydisch",
        scale.LocrianScale: "Lokrisch",
    }


    for root_note_template in notes_data:
        root_note = root_note_template["note"]
        root_display = pitch.Pitch(root_note).name.replace("-", "b")

        tasks = []

        for scale_type, german_name  in SCALE_NAME_MAP.items():
            try:
                scale_notes = generate_scale(root_note, scale_type)
                task = Task(
                    type="scales",
                    name=f"{root_note} {scale_type.__name__.replace('_', ' ')}",
                    display_name=f"{root_display} {german_name}",
                    root=root_note,
                    clef=clef,
                    data={"notes": scale_notes},
                )
                tasks.append(task)
                counter += 1
            
            except Exception as e:
                print(f"Error generating scale: {e}")

        db.session.bulk_save_objects(tasks)
        sse.publish({"progress": counter, "total": total, "message": f"Tonleitern ({root_note})"}, type="update")
        db.session.commit()

    print("Finished Scale Tasks")
    return counter

def generate_scale(root_note, scale: type[scale.Scale]):
    """
    Generate a scale using music21.scale.
    Supported scale types: "major", "minor", "harmonicMinor", "melodicMinor"
    """

    # Create the scale
    root = note.Note(root_note)
    generated_scale = scale(root) # type: ignore

    # Return all scale notes
    return [p.nameWithOctave for p in generated_scale.getPitches(root_note, root.transpose("P8").nameWithOctave)] # type: ignore




