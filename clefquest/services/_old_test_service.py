from models import Completion, CompletionTask, Task, db
import random


def initialize_completion(test, student_id, student_name):
    completion = Completion(
        student_id=student_id, # type: ignore
        student_name=student_name, # type: ignore
        test_id=test.id, # type: ignore
    )
    db.session.add(completion)
    for task_type, count in test.task_count.items():
        available_tasks = Task.query.filter_by(type=task_type).all()
        selected_tasks = random.sample(available_tasks, count)
        for task in selected_tasks:
            completion_task = CompletionTask(
                completion=completion, # type: ignore
                task_type=task.type, # type: ignore
                task_name=task.name, # type: ignore
                correct_answer=json.dumps(task.metadata)  # Adjust as needed # type: ignore
            )
            db.session.add(completion_task)
    db.session.commit()
    return completion


def get_next_task(completion_id):
    next_task = CompletionTask.query.filter_by(
        completion_id=completion_id, given_answer=None
    ).first()
    return next_task

def save_answer(task_id, given_answer):
    task = CompletionTask.query.get(task_id)
    task.given_answer = given_answer # type: ignore
    task.is_correct = given_answer == task.correct_answer  # type: ignore # Adjust logic for correctness
    db.session.commit()


def calculate_grade(completion_id):
    tasks = CompletionTask.query.filter_by(completion_id=completion_id).all()
    total_tasks = len(tasks)
    correct_tasks = sum(1 for task in tasks if task.is_correct)
    grade = correct_tasks / total_tasks
    completion = Completion.query.get(completion_id)
    completion.score = grade # type: ignore
    db.session.commit()
    return grade
