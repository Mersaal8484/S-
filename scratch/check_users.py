from django.contrib.auth import get_user_model
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elem.settings')
django.setup()

User = get_user_model()
users = User.objects.all()
print("Total users:", users.count())
for u in users:
    print(f"Username: {u.username}, Email: {u.email}, Staff: {u.is_staff}, Superuser: {u.is_superuser}")
