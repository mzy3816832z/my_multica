import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
import django; django.setup()
from apps.users.models import User
import bcrypt

user = User.objects.get(username='admin123')
user.set_password('3816832z')
user.save(update_fields=['password', 'updated_at'])
print(f'Password reset for {user.username}')

# Verify
user2 = User.objects.get(username='admin123')
result = user2.check_password('3816832z')
print(f'Verify result: {result}')
