# errors/error_mappers.py
from models.api_response_dto import APIResponse
from errors.http_status import HttpStatusCode
from errors.error_codes import ErrorCode

"""
Error Code to HTTP Status Transformer
-------------------------------------
Maps domain-specific error codes to standardized HTTP status codes for
consistent REST API behavior. Operates as a mutating transformer that:

1. Analyzes the first error in the APIResponse errors array
2. Maps business/logic errors to appropriate HTTP status codes
3. Updates the response code in-place for efficiency
4. Returns the modified response with proper HTTP semantics

This ensures clients receive meaningful HTTP status codes while maintaining
the original business error context for detailed troubleshooting.
"""

def map_error_code(api_response: APIResponse) -> APIResponse:
    if not api_response.errors:
        api_response.code = HttpStatusCode.OK
        return api_response

    # Get the first error code to determine HTTP status
    error_code = api_response.errors[0].code

    # ==================== ERROR CODE TO HTTP STATUS MAPPING ====================
    http_status_map = {
        # ==================== 400 - BAD REQUEST ERRORS ====================
        # Header validation errors
        ErrorCode.MISSING_HEADERS: HttpStatusCode.BAD_REQUEST,
        ErrorCode.MISSING_AUTHORIZATION_HEADER: HttpStatusCode.BAD_REQUEST,
        ErrorCode.INVALID_AUTHORIZATION_HEADER: HttpStatusCode.BAD_REQUEST,
        ErrorCode.EMPTY_AUTHORIZATION_HEADER: HttpStatusCode.BAD_REQUEST,
        ErrorCode.MISSING_REQUESTER_ID_HEADER: HttpStatusCode.BAD_REQUEST,
        ErrorCode.INVALID_REQUESTER_ID_HEADER: HttpStatusCode.BAD_REQUEST,
        ErrorCode.EMPTY_REQUESTER_ID_HEADER: HttpStatusCode.BAD_REQUEST,
        
        # Request format errors
        ErrorCode.INVALID_JSON_FORMAT: HttpStatusCode.BAD_REQUEST,
        
        # Business rule violations
        ErrorCode.ESCALATE_TO_LANE: HttpStatusCode.BAD_REQUEST,

        # ==================== 401 - UNAUTHORIZED ERRORS ====================
        ErrorCode.UNAUTHORIZED: HttpStatusCode.UNAUTHORIZED,

        # ==================== 404 - NOT FOUND ERRORS ====================
        ErrorCode.USER_NOT_FOUND: HttpStatusCode.NOT_FOUND,
        ErrorCode.WORK_ITEM_NOT_FOUND: HttpStatusCode.NOT_FOUND,
        ErrorCode.NO_ROWS_AFFECTED: HttpStatusCode.NOT_FOUND,

        # ==================== 409 - CONFLICT ERRORS ====================
        ErrorCode.CONFLICT: HttpStatusCode.CONFLICT,

        # ==================== 422 - UNPROCESSABLE ENTITY ERRORS ====================
        ErrorCode.VALIDATION_ERROR: HttpStatusCode.UNPROCESSABLE_ENTITY,

        # ==================== 500 - INTERNAL SERVER ERRORS ====================
        # Configuration errors
        ErrorCode.MISSING_ENV_VARS: HttpStatusCode.INTERNAL_SERVER_ERROR,
        
        # Database errors
        ErrorCode.DATABASE_ERROR: HttpStatusCode.INTERNAL_SERVER_ERROR,
        ErrorCode.COMMIT_TRANSACTION: HttpStatusCode.INTERNAL_SERVER_ERROR,
        
        # System/processing errors
        ErrorCode.INTERNAL_SERVER_ERROR: HttpStatusCode.INTERNAL_SERVER_ERROR,
        ErrorCode.SERIALIZE_EVENT_DATA: HttpStatusCode.INTERNAL_SERVER_ERROR,

        # ==================== 503 - SERVICE UNAVAILABLE ERRORS ====================
        ErrorCode.EXTERNAL_API_FAILED: HttpStatusCode.UNAUTHORIZED,
    }

    # Default to 500 if no match
    api_response.code = http_status_map.get(error_code, HttpStatusCode.INTERNAL_SERVER_ERROR)

    return api_response 