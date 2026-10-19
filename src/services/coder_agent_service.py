import uuid
from setting import config
from agents.code_generator_agent import CodeGeneratorAgent
from agents.code_reviewer_agent import CodeReviewerAgent
from agents.code_researcher_agent import CodeResearcherAgent
from langgraph.graph import StateGraph, END
from typing import TypedDict
from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.runnables import RunnableConfig
from models.request_dto import AgentRequest, AgentResponse
from utils.errors.error_log import log_error
from utils.errors.http_status import HttpStatusCode
from models.custome_app_exepction import CustomAppException
from utils.errors.error_codes import ErrorCode
from utils.llm_client import Llm
from models.request_dto import AgentRequest,GeneratorRequest,ReviewerRequest,ResearcherRequest
from utils.logger import get_logger

logger = get_logger(__name__)
MAX_ITERATIONS = 3
DB_URI =   (
            f"postgresql://{config.db_username}:"
            f"{config.db_password}@"
            f"{config.db_host}:"
            f"{config.db_port}/"
            f"{config.db_name}"
        )

def is_greeting(text: str) -> bool:
    greetings = ["hi", "hello", "hey", "good morning", "good evening"]
    return text.lower().strip() in greetings


def is_small_talk(text: str) -> bool:
    small_talk = ["how are you", "what's up", "who are you"]
    return any(x in text.lower() for x in small_talk)

class AgentState(TypedDict):
    request:str
    intent:str
    response:str
    research_output:str
    review_output:str
    review_status:str
    iterations:int
    thread_id: str

class AgentService:
    def __init__(self,llm,generator,reviewer,researcher):
        self.llm        = llm
        self.generator  = generator
        self.reviewer   = reviewer
        self.researcher = researcher
        self.graph      = None


    #  Intent 
    async def detect_intent(self, state: AgentState) -> AgentState:
        try:
            query = state["request"]
           
            logger.info("detecting intent..")
            

            prompt = f"""
                You are a strict intent classification system.
                Output ONLY one of these exact words, lowercase, no punctuation.

                INTENTS:
                - "code" = user wants code written, generated, or built
                - "review" = user wants their code reviewed, debugged, or fixed
                - "review_research" = user asks if a library or package usage is correct,
                                      or wants to know the right way to use a tool/library
                - "research" = user wants explanation, concepts, or docs only (no code)
                - "research_code" = user wants research/explanation AND code together
                - "unknown" =  greetings,casual talk, or unrelated queries

                RULES:
                1. Output ONLY one word, lowercase.
                2. No JSON, no punctuation, no explanation.
                3. If unsure, return: code

                EXAMPLES:
                Query: write a binary search = code
                Query: review this code: def foo(): ... = review
                Query: is this the correct way to use pandas?= review_research
                Query: am I using langchain correctly? = review_research
                Query: what is multithreading = research
                Query: explain caching and give code = research_code
                Query: how does numpy broadcasting work  = research
                Query: explain langchain and show me an example = research_code
                Query: {query}
                Output:
            """
            response = await self.llm.ainvoke(prompt)
            intent = response.content.strip().lower()
            valid = ["code", "review", "review_research", "research", "research_code"]
            if intent not in valid:
                intent = "unknown"



            logger.info(f"Intent detected: {intent}")
            routes = {
                "code":            "generator",
                "review":          "reviewer",
                "review_research": "researcher",
                "research":        "researcher",
                "research_code":   "researcher",
                "unknown": END,
            }
            next_node = routes.get(intent, END)
            update={"intent": intent}
            if intent == "unknown":
                update["response"]=("I can help with only tasks related to coding")
            return Command(
                update=update,
                goto=next_node,
            )

        except Exception as e:
            log_error("agent_service.py", "detect_intent", str(e))
            raise CustomAppException(
                message=f"Service error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
            )

    # Researcher
    async def code_researcher(self, state: AgentState) -> AgentState:
        try:

            logger.info("Researcher starting")
            request = ResearcherRequest(
                user_id= state["thread_id"],
                user_query= state["request"],
            )


            result = await self.researcher.code_researcher_agent(request)

        
            logger.info("Research completed")
            intent = state["intent"]

           
            if intent in ["research_code", "review_research"]:
                next_node = "generator"
            else:
                next_node = END

            return Command(
                update={"research_output": result.content},
                goto=next_node,
            )

        except Exception as e:
            log_error("agent_service.py", "code_researcher", str(e))
            raise CustomAppException(
                message=f"Researcher error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
            )

    # Coder 
    async def code_generator(self, state: AgentState) -> AgentState:
        try:
            print(state["thread_id"])
            request = GeneratorRequest(
            user_id          = state["thread_id"],
            user_query       = state["request"],
            review_notes     = state.get("review_output")
                               if state.get("review_status") == "fail" else None,
            research_context = state.get("research_output") or None,
        )
            logger.info("code Generator started ")

            result = await self.generator.code_generator_agent(request)
            
            logger.debug(f"coder output:\n{result.response}")
           
            state["response"] = result.response
            return state
        except Exception as e:
            log_error("agent_service.py", "code_generator", str(e))
            raise CustomAppException(
                message=f"Generator error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
            )

    #  Reviewer 
    async def code_reviewer(self, state: AgentState) -> AgentState:
        try:
            iteration = state.get("iterations", 0) + 1
            logger.info(f"starting review (iteration {state.get('iterations', 0) + 1})...")
            request = ReviewerRequest(
                user_id= state["thread_id"],
                user_query= state["request"],
                code = state.get("response") or state["request"]


            )
            logger.info("Code reviewer started")

            result = await self.reviewer.code_reviewer_agent(request)

            review_status = result.review_status
            logger.debug(f"reviewer output:\n{result}")
            logger.info(f"reviewer status: {review_status}")
            logger.info(f"iteration: {iteration} / {MAX_ITERATIONS}")

            # Decide next node
            if iteration >= MAX_ITERATIONS:
                logger.info("Max iterations reached")
                next_node = END
            elif  review_status.lower() == "pass":
                next_node = END    
            else:
                next_node = "generator"

            return Command(
                update={
                    "review_output": result.feedback,
                    "review_status": review_status,
                    "iterations": iteration,
                },
                goto=next_node,
            )

        except Exception as e:
            log_error("agent_service.py", "code_reviewer", str(e))
            raise CustomAppException(
                message=f"Reviewer error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
            )

    #  Entry point 
    async def coder_agent_service(self, request: AgentRequest):
        try:
            thread_id = request.user_id or str(uuid.uuid4())
            
            user_query = request.user_query.lower().strip()

           
            if is_greeting(user_query):
                return AgentResponse(
                    code="Hi  I'm your coding assistant. How can I help you?",
                    thread_id=request.user_id or ""
                )

            
            if is_small_talk(user_query):
                return AgentResponse(
                    code="I'm here to help you with coding, debugging, and research ",
                    thread_id=request.user_id or ""
                )

            async with AsyncPostgresSaver.from_conn_string(DB_URI, pipeline=False) as checkpointer:
                await checkpointer.setup()


                builder = StateGraph(AgentState)

                builder.add_node("intent",     self.detect_intent)
                builder.add_node("generator",  self.code_generator)
                builder.add_node("reviewer",   self.code_reviewer)
                builder.add_node("researcher", self.code_researcher)

                builder.set_entry_point("intent")

                builder.add_edge("generator", "reviewer")

                logger.info("Graph built successfully")
                graph = builder.compile(checkpointer=checkpointer)


                state = {
                    "request": request.user_query,
                    "intent": "",
                    "response": "",
                    "research_output": "",
                    "review_output": "",
                    "review_status": "",
                    "iterations": 0, 
                    "thread_id": thread_id
                }


                config: RunnableConfig = {
                    "configurable": {
                        "thread_id": thread_id,
                    }
                }

                result = await graph.ainvoke(state, config)
                print(graph.get_state_history(config))
             


                intent = result.get("intent", "")
                logger.info("Graph completed")
                logger.info(f"Total iterations: {result.get('iterations', 0)}")
                logger.info(f"Review status: {result.get('review_status', '')}")
                

                if intent == "research":
                    logger.info(f"research output:{result.get('research_output')}")
                    return AgentResponse(
                    code = result.get("response"),
                    research_output= result.get("research_output"),
                    thread_id = result.get("thread_id")
                    )

                elif intent == "review" and result.get("review_status") == "pass":
                    logger.info(f"code:{result.get('response')}\nreview output:{result.get('review_output')}")
                    return AgentResponse(code = result.get("response"),review_output=result.get("review_output"),thread_id = result.get("thread_id"))
                                            
                
                elif intent == "review" and  result.get("review_status") == "fail":
                    
                    logger.info(f"response:{result.get('response')}")
                    logger.info(f"code:{result.get('response')}\nreview output:{result.get('review_output')}\nresearch output:{result.get('research_output')}")
                    return AgentResponse(
                        code = result.get("response"),
                        review_output=result.get("review_output"),
                        thread_id = result.get("thread_id")
                    )
                    

                else:
                
                    logger.info(f"response:{result.get('response')}\nreview output:{result.get('review_output')}\n")
                    return AgentResponse(
                        code = result.get("response"),
                        research_output= result.get("research_output"),
                        review_output= result.get("review_output"),
                        thread_id = result.get("thread_id")

                    )


        except Exception as e:
            
            log_error("code_agent_service.py", "coder_agent_service", str(e))
            raise CustomAppException(
                message=f"Service error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
            )
