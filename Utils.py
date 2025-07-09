from venv import logger
from common.models import Course, Occupation
from django.core.files.uploadedfile import InMemoryUploadedFile

from users.models import UserAlbum
import logging

class Utils:
    
    @staticmethod
    def calculate_profile_completion(user):
        fields_to_check = [
            'first_name', 'last_name', 'dob', 'gender', 'mobile', 'email',
            'profile_image', 'height', 'weight', 'marital_status',
            'religion', 'caste', 'country', 'state', 'city', 'qualification',
            'occupation', 'income', 'food', 'smoking', 'drinking', 'about_me'
        ]

        filled_fields = sum([1 for field in fields_to_check if getattr(user, field, None)])
        total_fields = len(fields_to_check)
        
        return int((filled_fields / total_fields) * 100) if total_fields > 0 else 0

    @staticmethod
    def generate_career_data(request_data):
        try:
            response = {**request_data}
            specify_occupation = request_data.get('specify_occupation',None)
            if specify_occupation:
                occupation_data = Occupation.objects.create(name=specify_occupation)
                response["occupation"] = occupation_data.id
                del response["specify_occupation"]
            return response
        except:
            return None
  

    @staticmethod
    def prepare_album_data(user, profile_image, user_photos=None, is_private=False):
    
        if not profile_image or not isinstance(profile_image, InMemoryUploadedFile):
            raise ValueError("Primary profile picture is required")

        album_data = [{
            'user': user,
            'image': profile_image,
            'primary': UserAlbum.PrimaryphotoChoices.YES,
            'is_private': bool(is_private)
        }]

        if user_photos:
            for photo in user_photos[:6]: 
                if isinstance(photo, InMemoryUploadedFile):
                    album_data.append({
                        'user': user,
                        'image': photo,
                        'primary': UserAlbum.PrimaryphotoChoices.NO,
                        'is_private': bool(is_private)
                    })

        return album_data



        
