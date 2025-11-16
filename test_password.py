from django.contrib.auth import get_user_model

User = get_user_model()

# Test a few users
test_users = ['tendai_moyo', 'john_phiri', 'admin']

for username in test_users:
    try:
        user = User.objects.get(username=username)
        check = user.check_password('password123')
        admin_check = user.check_password('admin123')
        print(f"{username}:")
        print(f"  - password123: {check}")
        print(f"  - admin123: {admin_check}")
        print(f"  - Has usable password: {user.has_usable_password()}")
        print()
    except User.DoesNotExist:
        print(f"{username}: Does not exist\n")
