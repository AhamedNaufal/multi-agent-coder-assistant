import requests
from setting import config

def log_error(file_name,function_name,error_message):
    print(function_name,error_message)
    if not config.error_log_url:
        return
    try:
        requests.post(
            config.error_log_url,
            json = {
                "file_name": file_name,
                "function_name": function_name,
                "error_message": error_message
            },
            timeout=3
        )
    except Exception:
        pass