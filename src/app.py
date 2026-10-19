import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.coder_agent_router import router
from models.custome_app_exepction import CustomAppException
from utils.errors.http_status import HttpStatusCode
from models.api_response_dto import APIResponse, Error
from utils.errors.error_codes import ErrorCode, ErrorCodeStatus
from dotenv import load_dotenv

from utils.logger import setup_logger

setup_logger()

load_dotenv()

app = FastAPI(
    title="mcp Client API",
    version="1.0.0",
    
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
 
app.include_router(router)
 
# ==================== EXCEPTION HANDLERS ====================
@app.exception_handler(CustomAppException)
async def custom_exception_handler(request: Request, exc: CustomAppException):
    api_response = exc.to_api_response()
    return JSONResponse(status_code=exc.status_code, 
                        content=api_response.to_dict())
 
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append(Error(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"{error['loc'][-1]}: {error['msg']}",
            error_code_id=ErrorCodeStatus[ErrorCode.VALIDATION_ERROR]
        ))
    api_response = APIResponse(
        data=None,
        errors=errors,
        code=HttpStatusCode.UNPROCESSABLE_ENTITY
    )
    return JSONResponse(status_code=HttpStatusCode.UNPROCESSABLE_ENTITY, 
                        content=api_response.to_dict())
 
# ==================== MAIN ENTRY ====================
if __name__ == "__main__":
    uvicorn.run("app:app", 
                host="0.0.0.0", 
                port=8080, 
                reload=True)
