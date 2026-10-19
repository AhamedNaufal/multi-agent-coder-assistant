from fastapi import APIRouter, Depends
from models.api_response_dto import APIResponse
from models.request_dto import AgentRequest
from services.coder_agent_service import AgentService
from utils.errors.error_log import log_error
from utils.errors.http_status import HttpStatusCode
from models.custome_app_exepction import CustomAppException
from utils.errors.error_codes import ErrorCode
from utils.logger import get_logger
from dependency.dependency import get_agent_service
logger = get_logger(__name__)

 
router = APIRouter(prefix="/api/v1")
 
 
@router.post("/coder-agent")
async def coder_agent_router(request:AgentRequest,service: AgentService = Depends(get_agent_service)):
    
    try:
        logger.info("service function called")
        result = await service.coder_agent_service(request = request)
        return APIResponse(data= result,code= HttpStatusCode.OK).to_dict()

    except CustomAppException:
        raise
 
    except Exception as e:
        log_error("chatbot_router.py","router",str(e))
        raise CustomAppException(
            message=f"Router error: {str(e)}",
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
        )
 