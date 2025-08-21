from rest_framework.response import Response


def success_response(result=None, message="Success", status=200):
    response = {
        "status": status,
        "message": message,
    }

    # if isinstance(result, dict) and "data" in result:
    #     response["data"] = result.get("data", {})

    response["data"] = result.get("data", result) if isinstance(result, dict) else result

    return Response(response, status=status)


def error_response(message="Error", status=400):
    response = {
        "status": status,
        "message": message,
    }

    return Response(response, status=status)

def error_response_with_data(message="Error", data=None, status=400):
    """New function that includes error data without breaking existing code"""
    response = {
        "status": status,
        "message": message,
        "data": data if data else {}
    }
    return Response(response, status=status)

def server_error_response(message="Internal server error", error_detail=None):
    response = {
        "success": False,
        "message": message,
    }
    if error_detail:
        response["error"] = str(error_detail)
    return Response(response, status=500)

# def success_(message: str="success", response: dict={}):
#     res_array = {
#         "success": True,
#         "error_code": -1,
#         "message": message,
#         "data": response,
#     }
#     return res_array

# def error_(message: str="failed",error_code: int=1001,response: dict=None):
#     res_array = {
#         "success": False,
#         "error_code": error_code,
#         "message": message,
#         "data": response,
#     }
#     return res_array



def success_(message: str="success", response: dict={}):
    res_array = {
        "success": True,
        "error_code": -1,
        "message": message,
        "data": response,
    }
    return res_array
 
 
# returns error response
def error_(
    message: str="failed",
    error_code: int=1001,
    response: dict=None,
):
 
    res_array = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "data": response,
    }
    return res_array
