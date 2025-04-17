from datetime import datetime
from music21 import pitch

from sqlalchemy import Index
from extensions import db

from sqlalchemy.dialects.sqlite import JSON

# Groups are created by a teacher and filled with students by Patchwerk automatically. It is a "Klasse" or "Kurs"
# When a group is deleted, associated students and tests are removed.

# Use nanoid for all but tasks so they are not sequential but URL-safe

from nanoid import generate

def generate_nanoid():
    return generate(size=12)  # 12-char unique ID


class Group(db.Model):
    id = db.Column(db.String(12), primary_key=True, default=generate_nanoid, unique=True)
    name = db.Column(db.String, nullable=False)
    students = db.Column(db.JSON, nullable=False)  # List of student IDs and names
    teacher_id = db.Column(db.String, nullable=False)
    tests = db.relationship('Test', backref='group', lazy=True, cascade='all, delete-orphan')

# Tests belong to a group.  

class Test(db.Model):
    id = db.Column(db.String(12), primary_key=True, default=generate_nanoid, unique=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=True)

    open = db.Column(db.Boolean, default=True)
    piano = db.Column(db.Boolean, default=True)

    group_id = db.Column(db.String(12), db.ForeignKey('group.id'), nullable=False)

    quests = db.relationship('Quest', backref='test', lazy=True, cascade='all, delete-orphan')
    stages = db.relationship('Stage', backref='test', lazy=True, cascade='all, delete-orphan')


    def __repr__(self):
        return f"<Test id={self.id} title='{self.title}'>"
    

class Quest(db.Model):
    id = db.Column(db.String(12), primary_key=True, default=generate_nanoid, unique=True)
    student_id = db.Column(db.String, nullable=False)  # UUID from SSO
    student_name = db.Column(db.String, nullable=False)
    test_id = db.Column(db.String(12), db.ForeignKey('test.id'), nullable=False)
    start = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    tasks = db.relationship('Trial', backref='quest', lazy=True, cascade='all, delete-orphan')
    score = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<Quest id={self.id} student='{self.student_name}' test_id={self.test_id}>"


class Stage(db.Model):
    id = db.Column(db.String(12), primary_key=True, default=generate_nanoid, unique=True)
    test_id = db.Column(db.String(12), db.ForeignKey('test.id'), nullable=False)

    task_type = db.Column(db.String, nullable=False)  # "intervals", "triads", etc.
    count = db.Column(db.Integer, nullable=False)  # Number of tasks for this stage

    # Limits on pitch range (if applicable)
    lower_limit = db.Column(db.String, nullable=True)  # e.g., "C4"
    upper_limit = db.Column(db.String, nullable=True)  # e.g., "C6"
    clef = db.Column(db.String, nullable=False) 
    # difficulty = db.Column(db.Integer, nullable=False)

    # NEW: Task-type specific settings
    settings = db.Column(JSON, nullable=True)  # Example: {"accidentals": "Einfache", "intervals": ["m3", "M3"]}

    def __repr__(self):
        return f"<Stage id={self.id} test_id={self.test_id} task_type='{self.task_type} count={self.count} limits={self.lower_limit} and {self.upper_limit}'>"


class Trial(db.Model):
    id = db.Column(db.String(12), primary_key=True, default=generate_nanoid, unique=True)
    quest_id = db.Column(db.String(12), db.ForeignKey('quest.id'), nullable=False)
    task_id = db.Column(db.String(12), db.ForeignKey('task.id'), nullable=False)  # Reference to Task
    stage_id = db.Column(db.String(12), db.ForeignKey('stage.id'), nullable=False)
    
    task = db.relationship('Task', backref=db.backref('trials', lazy=True))  # Relationship to Task
    stage = db.relationship('Stage', backref=db.backref('trials', lazy=True))
    
    given_answer = db.Column(db.String, nullable=True)  # Student's answer
    possible_answers = db.Column(db.JSON, nullable=False) # List of all answers: ["False1", "False2", ...]
    correct_answer = db.Column(db.String, nullable=False) # String of correct Answer
    is_correct = db.Column(db.Boolean, nullable=True)  # Whether the answer was correct

    def __repr__(self):
        return f"<Trial id={self.id} task_id={self.task_id} quest_id={self.quest_id}>"


class Task(db.Model):   # Must not be changed or the musicxml will be out of sync
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False, index=True)  # e.g., 'triad', 'scale'
    name = db.Column(db.String, nullable=False)  # e.g., 'C-Dur'
    display_name = db.Column(db.String, nullable=False)  # e.g., 'C-Dur'
    root = db.Column(db.String, nullable=False)  # e.g., 'C4''
    lowest_midi = db.Column(db.Integer, nullable=True, index=True)
    highest_midi = db.Column(db.Integer, nullable=True, index=True)
    clef = db.Column(db.String, nullable=False, index=True) 

    data = db.Column(db.JSON, nullable=True)  # Additional data like inversions, intervals
    
    musicxml = db.Column(db.Text, nullable=True)  # Store the generated MusicXML
    accidentals = db.Column(db.Integer, nullable=False, default=0)
    most_complex_accidental = db.Column(db.Integer, nullable=False, default=0)

    # ✅ Multi-column index
    __table_args__ = (
        Index("idx_task_type_clef_midi", type, clef, lowest_midi, highest_midi),
    )

    def __init__(self, *args, **kwargs):
        """Override init to generate MusicXML on creation."""
        super().__init__(*args, **kwargs)
        self.generate_musicxml()
        self.calculate_note_range()
        self.calculate_accidentals()

    def generate_musicxml(self):
        """Generates and stores MusicXML for the task."""
        from services.musicxml import generate_task_musicxml
        self.musicxml = generate_task_musicxml(self)
    
    def calculate_note_range(self):
        """
        Calculates the lowest and highest pitches in the task based on the root and data.
        
        Returns:
            tuple: (lowest_pitch, highest_pitch) as music21.pitch.Pitch objects.
        """
        notes = [pitch.Pitch(self.root)]  # Start with the root pitch

        # Extract additional pitches from the data field if applicable
        if self.data:
            for note_name in self.data.get("notes", []):  # Assuming notes is a list of note names
                try:
                    notes.append(pitch.Pitch(note_name))
                except Exception:
                    print(f"I got an invalid pitch for Task {self.display_name}")
                    pass  # Ignore invalid pitches

        # Determine the range
        self.lowest_midi = min(n.midi for n in notes)
        self.highest_midi = max(n.midi for n in notes)

    def calculate_accidentals(self):
        """
        Calculates the number of accidentals and the most complex accidental for a given Task.
        
        Complexity Rules:
        - Natural (no accidental) = 0
        - Simple accidentals (♯, ♭) = 1
        - Double accidentals (𝄪, 𝄫) = 2
        - Double accidentals are more complex than multiple simple accidentals.

        Updates:
            task.accidentals (int): Total number of accidentals in all notes of the task.
            task.most_complex_accidental (int): Highest complexity level of any accidental.
        """
        if not hasattr(self, "accidentals"):
            self.accidentals = 0
        if not hasattr(self, "most_complex_accidental"):
            self.most_complex_accidental = 0
            
        accidentals_found = []

        def get_accidental_complexity(pitch_obj):
            if pitch_obj.accidental is None:                            # 0 if no accidental
                return 0  # Natural
            alter_value = pitch_obj.accidental.alter                    # Returns float (-2.0, -1.0, 0.0, 1.0, 2.0)
            if alter_value < 0.5:                                       # Treat Natural-Acc as 1.5
                alter_value = 1.5
            return abs(int(alter_value))                                # Convert alteration to integer (1 for ♯/♭, 2 for 𝄪/𝄫)

        if self.data and "notes" in self.data:                          # Check accidentals in `data` field
            for note_name in self.data["notes"]:
                try:
                    note_pitch = pitch.Pitch(note_name)
                    accidentals_found.append(get_accidental_complexity(note_pitch))
                except Exception:
                    continue  # Ignore invalid pitches

        if not accidentals_found:                                       # If no notes in  data, get root
            try:
                root_pitch = pitch.Pitch(self.root)
                accidentals_found.append(get_accidental_complexity(root_pitch))
            except Exception:
                pass  # Ignore errors in root note processing

        # Calculate total accidentals count
        self.accidentals = sum(1 for acc in accidentals_found if acc > 0)

        # Determine most complex accidental
        self.most_complex_accidental = max(accidentals_found, default=0)