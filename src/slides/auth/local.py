import os
import json
import base64
from cryptography.fernet import Fernet
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials


DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/presentations",
]


def local_oauth(
    credentials_path: str, encryption_key: bytes, scopes: list[str] = DEFAULT_SCOPES
) -> Credentials:
    """
    Opens a browser for Google OAuth, retrieves credentials to edit a Google Slides slideshow,
    and caches the encrypted credentials.

    Args:
        credentials_path (str): Path to the client credentials JSON file.
        encryption_key (bytes): Symmetric key for encrypting the cached credentials. Must be 32 bytes long.

    Returns:
        google.oauth2.credentials.Credentials: The authenticated credentials.
    """
    # Ensure the encryption key is base64-encoded and 32 bytes long
    if len(encryption_key) != 32:
        raise ValueError("Encryption key must be 32 bytes long.")
    encryption_key = base64.urlsafe_b64encode(encryption_key)

    # Cache file path
    cache_dir = os.path.expanduser("~/.config/slides")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "token.json")

    # Check if cached credentials exist
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            encrypted_data = f.read()
        fernet = Fernet(encryption_key)
        decrypted_data = fernet.decrypt(encrypted_data)
        cached_credentials = json.loads(decrypted_data)

        # Load and return cached credentials
        credentials = Credentials.from_authorized_user_info(cached_credentials, scopes)
        if credentials.valid:
            return credentials

    # Create the flow using the credentials JSON file
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes=scopes)

    # Run the flow to open the browser and get credentials
    credentials = flow.run_local_server(port=0)

    # Cache the credentials
    credentials_data = credentials.to_json()
    fernet = Fernet(encryption_key)
    encrypted_data = fernet.encrypt(credentials_data.encode())
    with open(cache_file, "wb") as f:
        f.write(encrypted_data)

    return credentials
