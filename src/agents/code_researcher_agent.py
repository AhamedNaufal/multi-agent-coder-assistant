from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from agents.research_prompt import ResearcherSystemPrompt
from models.custome_app_exepction import CustomAppException
from utils.errors.error_codes import ErrorCode
from utils.errors.error_log import log_error
from utils.errors.http_status import HttpStatusCode
from models.request_dto import  CodeResearcherResponse, ResearcherRequest
from setting import config
from utils.llm_client import Llm
from utils.logger import get_logger

logger = get_logger(__name__)

MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"

DB_URI =   (
            f"postgresql://{config.db_username}:"
            f"{config.db_password}@"
            f"{config.db_host}:"
            f"{config.db_port}/"
            f"{config.db_name}"
        )

class CodeResearcherAgent:
    def __init__(self,llm,prompt):
        self.prompt = prompt
        self.llm = llm
    
    def mcp_client(self):
        client = MultiServerMCPClient(
            {
                "mcp-client": {
                    "transport" : "streamable_http",
                    "url": MCP_SERVER_URL,
                }
            }
        )
        logger.info("mcp_client")
        return client
    async def load_mcp_components(self, session):
        logger.info("loading MCP tools...")       
        tools = await load_mcp_tools(session) 
        logger.info(f"tools loaded: {[t.name for t in tools]}")
        return tools
    
    
    async def run_agent(self,tools,llm, system_prompt,user_query,user_id):
        logger.info("creating checkpointer")
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup()
            logger.info("checkpointer coonected")
            agent = create_agent(
                model=llm,
                tools=tools,
                checkpointer=checkpointer,
                response_format= CodeResearcherResponse
             )
            logger.info("agent created")
            messages = [SystemMessage(content=system_prompt)]+ [HumanMessage(content = user_query)]
            logger.info(f"invoking with query:\n{user_query[:300]}...")

        
            result = await agent.ainvoke(
                    {"messages":messages},
                    {"configurable": {"thread_id": str(user_id)}}
                )
            logger.info("after Invoked")
        
            output =  result["structured_response"]
            logger.debug(f"Researcher agent output:\n{output}")
            return output
      

   
    async def code_researcher_agent(self, request: ResearcherRequest) -> CodeResearcherResponse:
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
            
        except Exception as e:
            log_error("code_researcher_agent.py","code_researcher_agent",str(e))
            raise CustomAppException(
                message=f"code reseacher Agent error : {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
                 
            )
