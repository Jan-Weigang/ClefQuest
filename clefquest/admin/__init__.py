from extensions import admin, db

from .views import TrialAdmin, QuestAdmin, TaskAdmin, TestAdmin, StageAdmin, GroupAdmin

def init_admin(app):
    from models import Group, Stage, Test, Task, Quest, Trial
    admin.init_app(app)
    admin.add_view(TrialAdmin(Trial, db.session))
    admin.add_view(QuestAdmin(Quest, db.session))
    admin.add_view(TaskAdmin(Task, db.session))
    admin.add_view(TestAdmin(Test, db.session))
    admin.add_view(StageAdmin(Stage, db.session))
    admin.add_view(GroupAdmin(Group, db.session))

