from typing import Union, Optional
from uuid import uuid4
from google.cloud.storage import Client
from google.auth.credentials import Credentials
from matplotlib.figure import Figure
from matplotlib.axes import Axes

import io
import datetime


def signed_url_for(
    image: Union[Axes, Figure, str],
    bucket: str,
    credentials: Credentials,
    prefix: Optional[str] = None,
    expiration: datetime.timedelta = datetime.timedelta(minutes=15),
) -> str:
    """
    Uploads an image to a GCS bucket and returns a signed URL.

    Args:
        image (Union[Axes, Figure, str]): The image to upload. Can be a matplotlib Axes, Figure, or file path.
        bucket (str): The name of the GCS bucket.
        credentials (Credentials): GCP credentials
        prefix (Optional[str]): Optional prefix for the blob name.

    Returns:
        str: A signed URL for the uploaded image.
    """
    client = Client(credentials=credentials)
    bucket_obj = client.bucket(bucket)

    # Generate a unique blob name
    blob_name = f"{prefix + '/' if prefix else ''}{uuid4()}"
    blob = bucket_obj.blob(blob_name)

    # Handle image input
    if isinstance(image, (Axes, Figure)):
        buf = io.BytesIO()
        if isinstance(image, Axes):
            image = image.get_figure()
        image.savefig(buf, format="png")
        buf.seek(0)
        blob.upload_from_file(buf, content_type="image/png")
    elif isinstance(image, str):
        blob.upload_from_filename(image)
    else:
        raise ValueError("Unsupported image type. Must be Axes, Figure, or file path.")

    return blob.generate_signed_url(expiration=expiration, version="v4")
