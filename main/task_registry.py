tasks = {}

class TaskType(object):

    def __init__(self, slug, description, form_class):
        self.slug = slug
        self.description = description
        self.form_class = form_class

def register_task(slug, description, form_class):
    tasks[slug] = TaskType(slug, description, form_class)

def get_task(slug):
    return tasks[slug]
