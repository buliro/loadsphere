import os
import django

def init_db():
    """Initialise Django and ensure an admin user exists.

    Args:
        None

    Returns:
        None: The function performs setup side effects only.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'route_planner.settings')
    django.setup()

    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Create admin user if it doesn't exist
    if not User.objects.filter(email='admin@example.com').exists():
        print("Creating admin user...")
        User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        print("Admin user created successfully!")
    else:
        print("Admin user already exists.")

if __name__ == "__main__":
    init_db()
