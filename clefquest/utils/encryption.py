from cryptography.fernet import Fernet

# Encryption setup
encryption_key = b'URvZnFTa7kkcFScDrDX-SZMCLAMvRMslNBSHMv8EjsQ='
cipher_suite = Fernet(encryption_key)

def encrypt_answer(answer):
    return cipher_suite.encrypt(answer.encode()).decode()

def decrypt_answer(encrypted_answer):
    return cipher_suite.decrypt(encrypted_answer.encode()).decode()