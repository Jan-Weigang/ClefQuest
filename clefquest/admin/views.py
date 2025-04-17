from flask_admin.contrib.sqla import ModelView
from decorators.auth import is_teacher_bool
from flask import session, redirect, url_for, abort


class ProtectedModelView(ModelView):
    """Base admin class that restricts access to teachers."""
    
    def is_accessible(self):
        """Check if the user is a teacher before allowing access."""
        if not is_teacher_bool():  # Use the boolean role check function
            raise abort(403)  # Raising an exception ensures the correct return type
        return True

    def inaccessible_callback(self, name, **kwargs):
        """This method is now unnecessary but kept for clarity."""
        raise abort(403)


class GroupAdmin(ProtectedModelView):
    # Specify the columns to display in the list view
    column_list = ('id', 'name', 'students', 'tests', 'teacher_id')
    
    # Specify the columns to allow editing
    form_columns = ('name', 'students')
    
    # Add column labels for better display
    column_labels = {
        'id': 'ID',
        'name': 'Group Name',
        'students': 'Students',
        'tests': 'Tests',
        'teacher_id': 'Teacher ID/sub'
    }

    # Optional: Add filters for easier navigation
    column_filters = ['name']


class TestAdmin(ProtectedModelView):
    column_list = ('id', 'title', 'description', 'group.name', 'open')
    form_columns = ('title', 'description', 'group_id', 'open')
    column_labels = {
        'id': 'ID',
        'title': 'Title',
        'description': 'Description',
        'group.name': 'Group Name',
        'open': 'Open',
    }
    column_filters = ['open', 'group.name']


class StageAdmin(ProtectedModelView):
    column_list = ('id', 'test_id', 'task_type', 'count', 'lower_limit', 'upper_limit', 'settings')
    column_labels = {
        'id': 'ID',
        'test_id': 'Test ID',
        'task_type': 'Task Type',
        'count': 'Task Count',
        'lower_limit': 'Lower Limit',
        'upper_limit': 'Upper Limit',
        'settings': 'Settings'
    }


class QuestAdmin(ProtectedModelView):
    column_list = ('id', 'student_id', 'student_name', 'test.title', 'start', 'end', 'score')
    column_labels = {
        'id': 'ID',
        'student_id': 'Student ID',
        'student_name': 'Student Name',
        'test.title': 'Test Title',
        'start': 'start',
        'end': 'end',
        'score': 'Score',
    }


class TrialAdmin(ProtectedModelView):
    # Specify the columns to display in the list view
    column_list = ('id', 'quest_id', 'task_id', 'task.type', 'task.name', 'possible_answers', 'correct_answer', 'given_answer', 'is_correct')
    
    # Specify the columns to allow editing
    form_columns = ('quest_id', 'task_id', 'given_answer', 'is_correct')
    
    # Add column labels for better display
    column_labels = {
        'id': 'ID',
        'quest_id': 'Quest ID',
        'task_id': 'Task ID',
        'task.type': 'Task Type',
        'task.name': 'Task Name',
        'possible_answers': 'Possible answers',
        'correct_answer': 'Correct Answer',
        'given_answer': 'Given Answer',
        'is_correct': 'Is Correct',
    }

from markupsafe import Markup
class TaskAdmin(ProtectedModelView):
    column_list = ('id', 'type', 'name', 'difficulty', 'root', 'display_name', 'musicxml_status', 'lowest_midi', 'highest_midi', 'accidentals', 'most_complex_accidental')
    column_labels = {
        'id': 'ID',
        'type': 'Task Type',
        'name': 'Task Name',
        'difficulty': 'Difficulty',
        'root': 'Root Note',
        'display_name': 'Display Name',
        'musicxml_status': 'MusicXML Available',
        'lowest_midi': 'Low Midi',
        'highest_midi': 'High midi',
        'accidentals': "Vorzeichen",
        'most_complex_accidental': "schwerstes Vorzeichen"
    }

    def musicxml_status(self, context, model, name):
        return Markup('<span style="color: green;">✔</span>') if model.musicxml else Markup('<span style="color: red;">✘</span>')

    column_formatters = {
        'musicxml_status': musicxml_status
    }
