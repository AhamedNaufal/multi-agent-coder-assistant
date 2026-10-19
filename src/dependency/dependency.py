
from fastapi import Depends
from functools import lru_cache
from utils.bedrock_client import Bedrock
from utils.llm_client import Llm
from agents.generator_prompt import GeneratorSystemPrompt
from agents.review_prompt import ReviewerSystemPrompt
from agents.research_prompt import ResearcherSystemPrompt
from agents.code_generator_agent import CodeGeneratorAgent
from agents.code_reviewer_agent import CodeReviewerAgent
from agents.code_researcher_agent import CodeResearcherAgent
from services.coder_agent_service import AgentService



@lru_cache()
def get_bedrock():
    return Bedrock()



def get_llm(bedrock: Bedrock = Depends(get_bedrock)):
    return Llm(bedrock=bedrock).get_llm()



def get_generator_prompt():
    return GeneratorSystemPrompt()


def get_reviewer_prompt():
    return ReviewerSystemPrompt()


def get_researcher_prompt():
    return ResearcherSystemPrompt()



def get_code_generator(
    llm = Depends(get_llm),
    prompt: GeneratorSystemPrompt = Depends(get_generator_prompt)):
    return CodeGeneratorAgent(llm=llm, prompt=prompt)


def get_code_reviewer(
    llm = Depends(get_llm),
    prompt: ReviewerSystemPrompt = Depends(get_reviewer_prompt)
):
    return CodeReviewerAgent(llm=llm, prompt=prompt)


def get_code_researcher(
    llm = Depends(get_llm),
    prompt: ResearcherSystemPrompt = Depends(get_researcher_prompt)
):
    return CodeResearcherAgent(llm=llm, prompt=prompt)


def get_agent_service(
    llm = Depends(get_llm),
    generator: CodeGeneratorAgent = Depends(get_code_generator),
    reviewer: CodeReviewerAgent = Depends(get_code_reviewer),
    researcher: CodeResearcherAgent = Depends(get_code_researcher),):
    return AgentService(llm=llm,generator=generator,reviewer=reviewer,researcher=researcher)