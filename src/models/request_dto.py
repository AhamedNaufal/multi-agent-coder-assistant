from typing import Literal, Optional
from pydantic import BaseModel

#  Shared 
class AgentRequest(BaseModel):
    user_id:str
    user_query: str

#  agent DTOs
class GeneratorRequest(BaseModel):
    user_id: str
    user_query: str
    review_notes: Optional[str] = None
    research_context: Optional[str] = None

class ReviewerRequest(BaseModel):
    user_id: str
    user_query: str
    code: str

class ResearcherRequest(BaseModel):
    user_id: str
    user_query: str

# Response 
class AgentResponse(BaseModel):
    code : Optional[str] = None
    research_output : Optional[str] = None
    review_output : Optional[str] = None
    thread_id: Optional[str] = None

class CodeReviewerResponse(BaseModel):
    feedback: str
    review_status: Literal["pass","fail"]
    changes: Optional[str] = None
    thread_id:Optional[str] = None
    

class CodeGenaratorResponse(BaseModel):
    response: str
    thread_id: Optional[str] = None
class CodeResearcherResponse(BaseModel):
    content: str
    thread_id:Optional[str] = None
   