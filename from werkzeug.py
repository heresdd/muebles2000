from werkzeug.security import generate_password_hash

password_a_cifrar = "CASINO4000" # <--- CAMBIA ESTO
hashed_password = generate_password_hash(password_a_cifrar)

print(hashed_password)