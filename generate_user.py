import hashlib
import os
import binascii

# Configurações
USERNAME = "admin".encode('utf-8')  # Correto: bytes
PASSWORD = "senha123"  # Senha em string (OK)

# Geração de salt (correto)
salt = os.urandom(32)  # 32 bytes aleatórios (Boa Prática)

# Geração de hash (correto)
key = hashlib.pbkdf2_hmac(
    'sha256',
    PASSWORD.encode('utf-8'),
    salt,
    100000  # Número adequado de iterações
)

# --------------------------------------------------
# *** Problema na Saída ***
# Conversão necessária para formato hexadecimal
# --------------------------------------------------
salt_hex = binascii.hexlify(salt).decode()  # Deve ter 64 caracteres (32 bytes)
key_hex = binascii.hexlify(key).decode()    # Ex: 'a1b2c3...'

# Verifique o comprimento
assert len(salt_hex) == 64, "Salt inválido!"
assert len(key_hex) == 64, "Key inválida!"

print(f"USUARIOS = {{")
print(f"    b'{USERNAME.decode()}': (")
print(f"        (bytes.fromhex('{salt_hex}'), bytes.fromhex('{key_hex}')),")
print(f"        'administrador'")
print(f"    )")
print(f"}}")