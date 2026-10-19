import os

import boto3
from utils.logger import get_logger

logger = get_logger(__name__)
class Bedrock:
    def __init__(self):
        self.client = None
    def get_bedrock_client(self):
        if self.client is None:
            self.client = boto3.client(
                service_name="bedrock-runtime",
                region_name=os.getenv("REGION"),
                aws_access_key_id =os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            logger.info("Bedrock client created")
        return self.client