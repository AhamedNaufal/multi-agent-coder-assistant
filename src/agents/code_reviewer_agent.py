from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from agents.review_prompt import ReviewerSystemPrompt
from models.custome_app_exepction import CustomAppException
from utils.errors.error_codes import ErrorCode
from utils.errors.error_log import log_error
from utils.errors.http_status import HttpStatusCode
from models.request_dto import  CodeReviewerResponse, ReviewerRequest
from setting import config
from utils.llm_client import Llm
from utils.logger import get_logger

logger = get_logger(__name__)
MCP_SERVER_URL = "http://127.0.0.1:8002/sse"

DB_URI =   (
            f"postgresql://{config.db_username}:"
            f"{config.db_password}@"
            f"{config.db_host}:"
            f"{config.db_port}/"
            f"{config.db_name}"
        )


class CodeReviewerAgent:
    def __init__(self,llm,prompt):
        self.prompt = prompt
        self.llm = llm
   
    
    def mcp_client(self):
        client = MultiServerMCPClient(
            {
                "mcp-client": {
                    "transport" : "sse",
                    "url": MCP_SERVER_URL,
                }
            }
        )
       
        return client
    async def load_mcp_components(self, session):
        tools = await load_mcp_tools(session) 
        blocked_tools = config.blocked_tools
        
        tools = [tool for tool in tools if tool.name not in blocked_tools]
        logger.info(f"tools loaded: {[t.name for t in tools]}")
        return tools
    
    
    async def run_agent(self,tools,llm, system_prompt,user_query,user_id):
      
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup()
            agent = create_agent(
                model=llm,
                tools=tools,
                checkpointer=checkpointer,
                response_format= CodeReviewerResponse

            )
            logger.info("agent created")
         
            messages = [SystemMessage(content=system_prompt)]+ [HumanMessage(content = user_query)]
            logger.info(messages)

            logger.info("before")
            result = await agent.ainvoke(
                    {"messages":messages},
                    {"configurable": {"thread_id": str(user_id)}}
                )
            logger.info("after")
           
            output =  result["structured_response"]
            logger.debug(f"reviewer agent output:\n{output}")
            return output
      

   
    async def code_reviewer_agent(self,request : ReviewerRequest) -> CodeReviewerResponse:
        try:
            user_query  = request.user_query
            user_id = request.user_id

            mcp_client = self.mcp_client()
            llm_client = self.llm
            system_prompt = self.prompt.get_system_prompt()
            async with mcp_client.session("mcp-client") as session:
                tools = await self.load_mcp_components(session)
                result = await self.run_agent(tools,llm_client,system_prompt,user_query,user_id)
                return result
                logger.info(str(e))
               
        except Exception as e:
            log_error("code_reviewer_agent.py","code_reviewer_agent",str(e))
            raise CustomAppException(
                message=f"code reviewer Agent error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
                 
            )
