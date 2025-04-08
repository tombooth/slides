import json
from google.cloud import secretmanager
from google.oauth2.service_account import Credentials


def from_secret(resource_name: str) -> Credentials:
    """
    Loads a service account JSON file from a secret in Google Secret Manager
    and sets up a Credentials object from it.

    Args:
        resource_name (str): The resource name of the secret in Google Secret Manager.

    Returns:
        google.oauth2.service_account.Credentials: The authenticated credentials.
    """
    # Initialize the Secret Manager client
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version
    response = client.access_secret_version(name=resource_name)

    # Decode the secret payload
    secret_payload = response.payload.data.decode("utf-8")

    # Parse the JSON and create the Credentials object
    service_account_info = json.loads(secret_payload)
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=[
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/devstorage.read_write",
        ],
    )

    return credentials
