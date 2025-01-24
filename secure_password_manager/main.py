import os
import base64
import hashlib
import getpass
import sqlite3
import random
import string
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Paths
MASTER_PASSWORD_FILE = "master_password.txt"
HASH_FILE = "master_password_hash.txt"
DATABASE_FILE = "passwords.db"
SETUP_MARKER_FILE = "setup_completed.txt"
MAX_ATTEMPTS = 3  # Max attempts before wiping the database

# Generate file hash
def generate_file_hash(filepath):
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()
    except FileNotFoundError:
        return None

# Save file hash
def save_file_hash(filepath, hashfile):
    file_hash = generate_file_hash(filepath)
    if file_hash:
        with open(hashfile, 'w') as f:
            f.write(file_hash)

# Verify file integrity
def verify_file_integrity(filepath, hashfile):
    if not os.path.exists(filepath) or not os.path.exists(hashfile):
        return False
    current_hash = generate_file_hash(filepath)
    try:
        with open(hashfile, 'r') as f:
            saved_hash = f.read().strip()
        return current_hash == saved_hash
    except FileNotFoundError:
        return False

# Check program setup status
def is_first_time_setup():
    return not os.path.exists(SETUP_MARKER_FILE)

# Mark setup as completed
def mark_setup_completed():
    with open(SETUP_MARKER_FILE, 'w') as f:
        f.write("SETUP_COMPLETED")

# Wipe database securely
def wipe_database():
    print("Wiping database and sensitive files...")
    
    # Wipe the database
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'wb') as f:
            f.write(os.urandom(os.path.getsize(DATABASE_FILE)))
        os.remove(DATABASE_FILE)
    
    # Remove the master password file
    if os.path.exists(MASTER_PASSWORD_FILE):
        os.remove(MASTER_PASSWORD_FILE)
    
    # Remove the setup marker file
    if os.path.exists(SETUP_MARKER_FILE):
        os.remove(SETUP_MARKER_FILE)
    
    # Remove the hash file
    if os.path.exists(HASH_FILE):
        os.remove(HASH_FILE)
    
    # Recreate the database
    create_database()
    
    print("Database and sensitive files have been wiped and recreated.")

# Store master password
def store_master_password(master_password):
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(master_password.encode())
    with open(MASTER_PASSWORD_FILE, 'wb') as f:
        f.write(base64.urlsafe_b64encode(salt) + b'\n')
        f.write(base64.urlsafe_b64encode(key))
    save_file_hash(MASTER_PASSWORD_FILE, HASH_FILE)

# Verify master password
def verify_master_password(master_password):
    try:
        with open(MASTER_PASSWORD_FILE, 'rb') as f:
            salt = base64.urlsafe_b64decode(f.readline().strip())
            stored_key = base64.urlsafe_b64decode(f.readline().strip())
        kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=100000)
        derived_key = kdf.derive(master_password.encode())
        return derived_key == stored_key
    except FileNotFoundError:
        return False

# Check or generate master password
def check_or_generate_master_password():
    if not os.path.exists(MASTER_PASSWORD_FILE) and not os.path.exists(HASH_FILE) and not os.path.exists(SETUP_MARKER_FILE):
        print("Critical files missing! Possible tampering detected.")
        wipe_database()
        
        # After wiping the database, generate a new master password
        print("Generating a new master password...")
        master_password = create_master_password()
        print(f"Your new master password is: {master_password}")
        
        # Store the new master password securely
        store_master_password(master_password)
        mark_setup_completed()
        print("Master password saved securely.")
        return master_password

    if is_first_time_setup():
        print("First-time setup detected. Generating a new master password...")
        master_password = create_master_password()
        print(f"Your new master password is: {master_password}")
        store_master_password(master_password)
        mark_setup_completed()
        print("Master password saved securely.")
        return master_password

    if not os.path.exists(MASTER_PASSWORD_FILE) or not os.path.exists(HASH_FILE):
        print("Error: Critical files are partially missing! Possible tampering detected.")
        exit(1)

    if not os.path.exists(HASH_FILE):
        print("Hash file missing. Recreating hash...")
        save_file_hash(MASTER_PASSWORD_FILE, HASH_FILE)

    if not verify_file_integrity(MASTER_PASSWORD_FILE, HASH_FILE):
        print("Error: Master password file integrity check failed! Possible tampering detected.")
        exit(1)

    attempts = 0
    while attempts < MAX_ATTEMPTS:
        master_password = getpass.getpass("Enter your master password: ")
        if verify_master_password(master_password):
            print("Master password verified successfully.")
            return master_password
        else:
            attempts += 1
            print(f"Invalid master password. {MAX_ATTEMPTS - attempts} attempts remaining.")
            if attempts >= MAX_ATTEMPTS:
                print("Too many incorrect attempts. Wiping the database...")
                wipe_database()
                exit(1)

# Create master password
def create_master_password(length=16):
    if length < 12:
        raise ValueError("Master password length should be at least 12 characters for security.")
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = string.punctuation
    all_characters = lower + upper + digits + special
    password = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special)
    ]
    password += random.choices(all_characters, k=length - len(password))
    random.shuffle(password)
    return ''.join(password)

# Encrypt data
def encrypt_data(key, plaintext):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
    return ciphertext, iv

# Decrypt data
def decrypt_data(key, ciphertext, iv):
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv))
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()

# Add password to the database
def add_password(master_password, url, username, plaintext_password):
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(master_password.encode())
    ciphertext, iv = encrypt_data(key, plaintext_password)
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO passwords (url, username, password, salt, iv) VALUES (?, ?, ?, ?, ?)',
                   (url, username, ciphertext, salt, iv))
    conn.commit()
    conn.close()

# Retrieve password from the database
def retrieve_password(master_password, url):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT username, password, salt, iv FROM passwords WHERE url = ?', (url,))
    result = cursor.fetchone()
    conn.close()
    if result:
        username, ciphertext, salt, iv = result
        kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=100000)
        key = kdf.derive(master_password.encode())
        plaintext_password = decrypt_data(key, ciphertext, iv).decode()
        return username, plaintext_password
    else:
        return None, None

# Create the database
def create_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS passwords (
                        id INTEGER PRIMARY KEY,
                        url TEXT NOT NULL,
                        username TEXT NOT NULL,
                        password BLOB NOT NULL,
                        salt BLOB NOT NULL,
                        iv BLOB NOT NULL)''')
    conn.commit()
    conn.close()

# Main function
def main():
    create_database()
    master_password = check_or_generate_master_password()
    
    while True:
        print("\nMenu:")
        print("1. Add a password")
        print("2. Retrieve a password")
        print("3. Generate a secure password")
        print("4. Exit")
        choice = input("Enter your choice: ")
        
        if choice == '1':
            url = input("Enter URL: ")
            username = input("Enter username: ")
            plaintext_password = input("Enter password: ")
            add_password(master_password, url, username, plaintext_password)
            print("Password added successfully.")
        elif choice == '2':
            url = input("Enter URL: ")
            username, plaintext_password = retrieve_password(master_password, url)
            if username:
                print(f"Username: {username}")
                print(f"Password: {plaintext_password}")
            else:
                print("No password found for the given URL.")
        elif choice == '3':
            generated_password = create_master_password()
            print(f"Generated secure password: {generated_password}")
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()