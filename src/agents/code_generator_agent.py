from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, SystemMessage
from agents.generator_prompt import GeneratorSystemPrompt
from models.custome_app_exepction import CustomAppException
from utils.bedrock_client import Bedrock
from utils.errors.error_codes import ErrorCode
from utils.errors.error_log import log_error
from utils.errors.http_status import HttpStatusCode
from models.request_dto import  CodeGenaratorResponse, GeneratorRequest
from setting import config
from utils.llm_client import Llm
from utils.logger import get_logger

logger = get_logger(__name__)

DB_URI =   (
            f"postgresql://{config.db_username}:"
            f"{config.db_password}@"
            f"{config.db_host}:"
            f"{config.db_port}/"
            f"{config.db_name}"
        )

class CodeGeneratorAgent:
    def __init__(self,llm,prompt):
        self.prompt = prompt
        self.llm = llm
    
    
    
    async def run_agents(self,llm_client, system_prompt,user_query,user_id):
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:

            await checkpointer.setup()
            agent = create_agent(
                model=llm_client,
                tools=[],
                checkpointer=checkpointer,
                response_format=CodeGenaratorResponse
            
            )
            messages = [SystemMessage(content=system_prompt)] + [HumanMessage(content = user_query)]
            
            result = await agent.ainvoke(
                    {"messages":messages},
                    {"configurable": {"thread_id": user_id}}
                )
            structured = result["structured_response"]
            logger.debug(f"coder Agent output:\n{structured.response}")
            return structured
    async def code_generator_agent(self,request:  GeneratorRequest) -> CodeGenaratorResponse:
        try:
            user_query  = request.user_query
            user_id = request.user_id
            if request.research_context:
                user_query += "\n\nResearch context:\n" + request.research_context
             

            if request.review_notes:
                user_query += "\n\nFix these issues:\n" + request.review_notes
              
            llm_client = self.llm
            system_prompt = self.prompt.get_system_prompt()
            result = await self.run_agents(llm_client,system_prompt,user_query,user_id)
           
            return result
        except Exception as e:
            log_error("code_generator_agent.py","chatbot_agent",str(e))
            raise CustomAppException(
                message=f"generator Agent error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
                 
            )
