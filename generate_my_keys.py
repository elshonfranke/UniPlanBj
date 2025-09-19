# generate_my_keys.py
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def generate_vapid_keys():
    """Génère une paire de clés VAPID (privée et publique) en utilisant la cryptographie."""
    # Génère une clé privée sur la courbe P-256, qui est la norme pour VAPID
    private_key = ec.generate_private_key(ec.SECP256R1())

    # Dérive la clé publique à partir de la clé privée
    public_key = private_key.public_key()

    # Formate la clé publique au format non compressé requis
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    # Encode les clés en base64 URL-safe, sans padding
    private_key_b64 = base64.urlsafe_b64encode(private_key.private_numbers().private_value.to_bytes(32, 'big')).rstrip(b'=').decode('utf-8')
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).rstrip(b'=').decode('utf-8')

    return private_key_b64, public_key_b64

private, public = generate_vapid_keys()

print("Clés VAPID générées avec succès !")
print("---------------------------------")
print(f"Clé Publique (VAPID_PUBLIC_KEY): {public}")
print(f"Clé Privée (VAPID_PRIVATE_KEY): {private}")
print("---------------------------------")
print("\nCopiez ces clés dans votre fichier de configuration.")
