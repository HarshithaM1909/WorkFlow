from django.apps import AppConfig

class EmpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emp'

    def ready(self):
        # Import the signals file so Django registers the receivers on startup
        import emp.signals
