from workers.serializers import UserRegistrationSerializer

# Test 1: Valid registration
print("=" * 60)
print("TEST 1: Valid Registration")
print("=" * 60)
data1 = {
    'username': 'valid_user',
    'email': 'valid@example.com',
    'password': 'ValidPass123',
    'password2': 'ValidPass123',
    'first_name': 'Valid',
    'last_name': 'User',
    'current_role': 'provider'
}
serializer1 = UserRegistrationSerializer(data=data1)
print(f"Is Valid: {serializer1.is_valid()}")
if serializer1.is_valid():
    try:
        user = serializer1.save()
        print(f"✅ User created: {user.username} ({user.get_full_name()})")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.current_role}")
    except Exception as e:
        print(f"❌ Error creating user: {e}")
else:
    print(f"❌ Validation errors: {serializer1.errors}")

# Test 2: Password mismatch
print("\n" + "=" * 60)
print("TEST 2: Password Mismatch")
print("=" * 60)
data2 = {
    'username': 'mismatch_user',
    'email': 'mismatch@example.com',
    'password': 'Pass123',
    'password2': 'DifferentPass123',
    'first_name': 'Mismatch',
    'last_name': 'User',
    'current_role': 'client'
}
serializer2 = UserRegistrationSerializer(data=data2)
print(f"Is Valid: {serializer2.is_valid()}")
if not serializer2.is_valid():
    print(f"✅ Correctly rejected - Errors: {serializer2.errors}")
else:
    print("❌ Should have been rejected!")

# Test 3: Duplicate username
print("\n" + "=" * 60)
print("TEST 3: Duplicate Username")
print("=" * 60)
data3 = {
    'username': 'tendai_moyo',  # Existing user
    'email': 'duplicate@example.com',
    'password': 'Pass123',
    'password2': 'Pass123',
    'first_name': 'Duplicate',
    'last_name': 'User',
    'current_role': 'client'
}
serializer3 = UserRegistrationSerializer(data=data3)
print(f"Is Valid: {serializer3.is_valid()}")
if not serializer3.is_valid():
    print(f"✅ Correctly rejected - Errors: {serializer3.errors}")
else:
    print("❌ Should have been rejected!")

# Test 4: Missing required fields
print("\n" + "=" * 60)
print("TEST 4: Missing Required Fields")
print("=" * 60)
data4 = {
    'username': 'incomplete_user',
    'password': 'Pass123',
    'password2': 'Pass123'
    # Missing email, first_name, last_name, current_role
}
serializer4 = UserRegistrationSerializer(data=data4)
print(f"Is Valid: {serializer4.is_valid()}")
if not serializer4.is_valid():
    print(f"✅ Correctly rejected - Errors: {serializer4.errors}")
else:
    print("❌ Should have been rejected!")

print("\n" + "=" * 60)
print("REGISTRATION TESTS COMPLETE")
print("=" * 60)
