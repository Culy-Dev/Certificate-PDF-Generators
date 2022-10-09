"""Module with functions to ultimate create a url the pdf files located in the AWS server"""

import boto3
import base64
import os
import logging
from urllib.parse import quote
from dotenv import load_dotenv
from botocore.client import Config

load_dotenv()

AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

logger = logging.getLogger(F'LinkedInAssignDueDateUpdate.{__name__}')

# AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

def get_s3_client():
    """Create a low-level service client by name using the default session.

    Returns:
        (class): Service client instance
    """
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )
    return s3_client

def transfer_cert_to_aws(cert_base64, name):
    """Adds an object to the bucket

    Args:
        cert_base64: base64 of certificate to be added to AWS
        name (str): name of the certificate

    Returns:
        url (str): url to the pdf of the certificate
    """
    s3_client = get_s3_client()

    response = s3_client.put_object(
        Bucket=AWS_S3_BUCKET,
        Key=f"{name}.pdf",
        Body=base64.b64decode(cert_base64),
        ACL='public-read',
        ContentType='application/pdf'
    )
    try: 
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 200:
            url = f'https://{AWS_S3_BUCKET}.s3.amazonaws.com/{quote(name)}.pdf'
            logger.info(f"Successful S3 put_object response. Status - {status}") 
            return url
        else:
            logger.info(f"Unsuccessful S3 put_object response. Status - {status}")
            return None
    except Exception as e:
        logger.error(e, exc_info=True)
        pass
    
