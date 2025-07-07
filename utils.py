import hashlib
import random
import string

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def generate_join_code(length=6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
def generate_join_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))