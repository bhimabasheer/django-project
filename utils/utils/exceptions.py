from rest_framework.serializers import ValidationError
 
class CustomValidation(ValidationError):
    def __init__(self, detail: str, status_code: int=None):
        self.detail = detail
 
        if status_code != None:
            self.status_code = status_code
