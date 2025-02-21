from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username

    @staticmethod
    def get(username):
        load_dotenv()
        stored_username = os.getenv('ADMIN_USERNAME')
        if stored_username and username == stored_username:
            return User(username)
        return None

    @staticmethod
    def verify_password(password):
        load_dotenv()
        stored_hash = os.getenv('ADMIN_PASSWORD_HASH')
        if stored_hash and check_password_hash(stored_hash, password):
            return True
        return False

def init_admin_account():
    """Initialize admin account if it doesn't exist"""
    load_dotenv()
    
    if not os.getenv('ADMIN_USERNAME') or not os.getenv('ADMIN_PASSWORD_HASH'):
        username = os.getenv('ADMIN_USERNAME', 'admin')
        default_password = 'admin'  # This should be changed immediately
        password_hash = generate_password_hash(default_password)
        
        with open('.env', 'a') as f:
            f.write(f'\nADMIN_USERNAME={username}\n')
            f.write(f'ADMIN_PASSWORD_HASH={password_hash}\n')
        
        print("Admin account created with default credentials:")
        print(f"Username: {username}")
        print(f"Password: {default_password}")
        print("Please change these credentials immediately in the settings page.")
