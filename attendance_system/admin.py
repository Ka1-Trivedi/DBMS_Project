from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
print(bcrypt.generate_password_hash("Kavan#17122005").decode('utf-8'))