import os

from langchain_aws import ChatBedrock

from utils.bedrock_client import Bedrock
from utils.logger import get_logger

logger = get_logger(__name__)

class Llm:
     def __init__(self,bedrock):
         self.bedrock = bedrock
         
     def get_llm(self,max_tokens=8000, temperature=0.2):

        llm = ChatBedrock(
            client=self.bedrock.get_bedrock_client(),
            model_id=os.getenv("MODEL_ID"),
            provider="amazon",
            model_kwargs={
                "maxTokenCount": max_tokens,
                "temperature": temperature,
            },
        )
        logger.info("llm client created")
        return llm