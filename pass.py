from django.contrib.auth.hashers import make_password

hashed = make_password("MySecretPassword123")
print(hashed)
