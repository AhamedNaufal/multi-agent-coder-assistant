import requests

def log_error(file_name,function_name,error_message):
    try:
        print(function_name,error_message)
        requests.post(
            "http://localhost:8001/api/v1/error",
            json = {
                "file_name": file_name,
                "function_name": function_name,
                "error_message": error_message
            }
        )
    except:
        pass