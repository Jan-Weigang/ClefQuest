from music21 import note, chord, interval, instrument, meter, clef, scale, pitch
from music21.stream.base import Stream
import random
from pathlib import Path
from models import Task

from music21.musicxml.m21ToXml import GeneralObjectExporter

def generate_triad_stream(s, task: Task):
    display_format = task.data.get("arpeggiated", None)

    if display_format == "random":
        display_format = random.choice(["chord", "arpeggio"])

    # Add notes based on display format
    if display_format:
        # Add notes sequentially (as an arpeggio)
        for n in task.data["notes"]:
            s.append(note.Note(n))
    else:
        # Add all notes at the same time (as a chord)
        c = chord.Chord(task.data["notes"])
        c.quarterLength = 2.0
        s.append(c)

    return s


def generate_task_musicxml(task: Task):
    # Generate MusicXML for the selected triad
    s = Stream()
    custom_instrument = instrument.Instrument()
    custom_instrument.instrumentName = " "
    s.append(custom_instrument)

    # Clef mapping
    clef_map = {
        "treble": clef.TrebleClef(),
        "bass": clef.BassClef(),
        "alto": clef.AltoClef(),
        "percussion": clef.PercussionClef(),
        "treble-8": clef.Treble8vbClef(),
        "treble+8": clef.Treble8vaClef(),
    }

    # Get clef from map or default to TrebleClef
    selected_clef = clef_map.get(task.clef, clef.TrebleClef())
    s.append(selected_clef)

    match task.type:

        case "triads":
            s = generate_triad_stream(s, task)

        case "note-reading":
            n = note.Note(task.root) # type: ignore
            n.quarterLength = 1.0
            s.append(n)

        case "intervals":
            # Add the root note
            root_note = note.Note(task.root)
            root_note.quarterLength = 1.0

            # Calculate the interval's target note
            interval_name = task.name  # Example: M3, P5
            interval_obj = interval.Interval(interval_name)
            target_note = interval_obj.transposeNote(root_note)

            # Add the target note
            target_note.quarterLength = 1.0

            arpeggiated = task.data.get("arpeggiated", None)

            match arpeggiated:

                case "up":
                    s.append(root_note)
                    s.append(target_note)
            
                case "down":
                    s.append(target_note)
                    s.append(root_note)
                
                case _:
                    chord_obj = chord.Chord([root_note, target_note])
                    chord_obj.quarterLength = 2.0
                    s.append(chord_obj)

        case "scales":
            s.append(meter.TimeSignature('8/4')) # type: ignore
            scale_notes = [note.Note(n) for n in task.data["notes"]]
            for n in scale_notes:
                        n.quarterLength = 1.0  # Play ascending scale
                        s.append(n)
            
            arpeggiated = task.data.get("arpeggiated", None)

        case _:
            print("Reached an impossible case during Task generation")
    

    # Fill the measure to 4/4 if needed
    total_duration = sum([n.quarterLength for n in s.notes])
    if total_duration < 4.0:  # 4/4 time signature
        s.append(note.Rest(quarterLength=(4.0 - total_duration)))

    # Convert Stream to MusicXML as a string
    musicxml_str = GeneralObjectExporter().parse(s).decode("utf-8")
    return musicxml_str




from sqlalchemy import and_

# This used additional queries. Not Needed if supplied with query result.
def get_false_answers_legacy(selected_task, root_letter_filter=True, max_false_answers=3):
    """
    Get false answers for a given task type and selected task.
    
    Args:
        task_type (str): The type of the task (e.g., 'triad', 'note-reading').
        selected_task (Task): The selected task for which false answers are generated.
        root_letter_filter (bool): Whether to filter by the first letter of the root.
        max_false_answers (int): Maximum number of false answers to return.

    Returns:
        list: A list of false answer display names.
    """
    # Build query filters
    filters = [Task.type == selected_task.type, Task.id != selected_task.id]

    # Add root letter filter if specified
    if root_letter_filter:
        correct_root_letter = selected_task.root[0].upper()
        filters.append(Task.root.startswith(correct_root_letter))

    # Query the database with the filters
    false_tasks = Task.query.filter(and_(*filters)).all()

    # Handle different task types separately
    if selected_task.type == "intervals":
        false_tasks = filter_false_intervals(selected_task, false_tasks)

    # Extract display names and ensure the correct answer is not included
    correct_answer = selected_task.display_name
    false_answers = list(set(task.display_name for task in false_tasks if task.display_name != correct_answer))

    
    # Randomly sample up to the max number of false answers
    return random.sample(false_answers, min(max_false_answers, len(false_answers)))


def get_false_answers(selected_task, filtered_tasks, root_letter_filter=True, max_false_answers=3):
    """
    Get false answers for a given task type and selected task.

    Args:
        selected_task (Task): The selected task for which false answers are generated.
        filtered_tasks (list[Task]): The already filtered list of tasks for the stage.
        root_letter_filter (bool): Whether to filter by the first letter of the root.
        max_false_answers (int): Maximum number of false answers to return.

    Returns:
        list: A list of false answer display names.
    """

    # Filter out the correct task
    all_false_tasks = [task for task in filtered_tasks if task.id != selected_task.id]

    chosen_false_tasks = all_false_tasks

    # # Apply root letter filter if enabled
    # if root_letter_filter:
    #     correct_root_letter = selected_task.root[0].upper()
    #     chosen_false_tasks = [task for task in all_false_tasks if task.root.startswith(correct_root_letter)]

    # Apply root letter filter
    if root_letter_filter:
        correct_root_letter = pitch.Pitch(selected_task.root).name
        chosen_false_tasks = [task for task in all_false_tasks if pitch.Pitch(task.root).name == correct_root_letter]

    # Handle different task types separately
    if selected_task.type == "intervals":
        chosen_false_tasks = filter_false_intervals(selected_task, chosen_false_tasks)

    # Extract display names and remove duplicates
    correct_answer = selected_task.display_name
    false_answers = list(set(task.display_name for task in chosen_false_tasks if task.display_name != correct_answer))
    all_false_answers = list(set(task.display_name for task in all_false_tasks if task.display_name != correct_answer))

    chosen_false_answers = random.sample(false_answers, min(max_false_answers, len(false_answers)))

    number_answers_to_add = max_false_answers - len(chosen_false_answers)

    # Addes additional answers that do not match the root
    # if number_answers_to_add > 0 and selected_task.type != "intervals":
    #     print(f"had to ignore root filter for task {selected_task} with only {len(chosen_false_tasks)} false answers with root.")

    #     remaining_false_answers = list(set(all_false_answers) - set(chosen_false_answers))
    #     additional_answers  = random.sample(remaining_false_answers, min(number_answers_to_add, len(remaining_false_answers)))
    #     chosen_false_answers.extend(additional_answers)

    return chosen_false_answers


def filter_false_intervals(selected_task, false_tasks):
    """
    Filters false interval tasks so they stay within the correct interval type range.

    Args:
        selected_task (Task): The selected interval task.
        false_tasks (list): A list of possible false answers.

    Returns:
        list: A filtered list of false interval tasks.
    """
    try:
        correct_interval = interval.Interval(selected_task.name)
    except:
        print("Tried to filter false intervals, could not create interval")
        return false_tasks  # If the interval is invalid, just return the existing options.

    print(f"Interval is {interval.Interval(correct_interval.semitones)}")
    # Define valid interval range (e.g., ±1 step up/down)
    min_interval = interval.Interval(correct_interval.semitones - 4)
    max_interval = interval.Interval(correct_interval.semitones + 4)

    # Filter only false answers that are within the allowed range
    filtered_answers = [
        task for task in false_tasks
        if min_interval.semitones <= interval.Interval(task.name).semitones <= max_interval.semitones
    ]

    return filtered_answers if filtered_answers else false_tasks  # Fallback if no valid false answers


def get_false_scale_answers(selected_task, stage, max_false_answers=3):
    """
    Get false answers based on root similarity and scale type.

    Args:
        selected_task (Task): The selected task for which false answers are generated.
        filtered_tasks (list[Task]): The already filtered list of tasks for the stage.
        max_false_answers (int): Maximum number of false answers to return.

    Returns:
        list: A list of false answer display names.
    """
    SCALE_NAME_MAP = {
        "MajorScale": "Dur",
        "MinorScale": "Moll",
        "MelodicMinorScale": "Melodisch Moll",
        "HarmonicMinorScale": "Harmonisch Moll",
        "DorianScale": "Dorisch",
        "PhrygianScale": "Phrygisch",
        "LydianScale": "Lydisch",
        "MixolydianScale": "Mixolydisch",
        "LocrianScale": "Lokrisch",
    }


    # Extract settings, ensuring it is a dictionary
    settings = stage.settings if isinstance(stage.settings, dict) else {}

    # Extract allowed scales safely
    allowed_scales = settings.get("scales", [])

    
    # Convert allowed scale names using the SCALE_NAME_MAP
    allowed_scale_names = {SCALE_NAME_MAP.get(scale_name, scale_name) for scale_name in allowed_scales}

    if not allowed_scale_names:
        print("Warning: No valid scales found in settings.")
        return []

    # Convert selected root to MIDI
    selected_root_midi = pitch.Pitch(selected_task.root).midi

    # Generate potential false roots (±2 semitones)
    possible_false_roots = [
        pitch.Pitch(midi).name for midi in range(selected_root_midi - 2, selected_root_midi + 3)
        if midi != selected_root_midi
    ]

    # Randomly pick `max_false_answers` unique false answers
    false_answers = set()
    while len(false_answers) < max_false_answers and possible_false_roots:
        false_root = random.choice(possible_false_roots)
        false_scale = random.choice(list(allowed_scale_names))
        false_answers.add(f"{false_root} {false_scale}")

    return list(false_answers)

