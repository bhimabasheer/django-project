from common.models import Course, Occupation
from user_preference.models import UserPartnerPreference
from django.db.models import Q
from django.db.models import F, ExpressionWrapper, FloatField
from click_for_marry import constants as const
from django.utils.timezone import now, timedelta
from users.models import Users, UsersInterests, UsersPersonality, UserAlbum
from django.db.models.functions import Concat, Floor, Round, Cast
from django.db.models import Q, Value, F, Max, CharField
from django.core.files.uploadedfile import InMemoryUploadedFile

from utils.api_response import error_
import ast

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
    def height_to_inches():
        inches = ExpressionWrapper(F('height') / 2.54, output_field=FloatField())

        # Get the feet part
        feet = Floor(inches / 12)

        # Get the remaining inches part
        remaining_inches = ExpressionWrapper(
            inches - (feet * 12),
            output_field=FloatField()
        )

        return feet,remaining_inches

    def build_preference_match_query(user):
        filter_query = Q()
        preferences = UserPartnerPreference.objects.filter(user=user)
        if preferences.exists():
            preferences = preferences.select_related("religion", "country_living", "annual_income",\
                            "family_type", "family_status", "marital_status", "body_type", "diet", \
                            "community", "complexion")
            user_preference = preferences.first()
            # Age
            if user_preference.age:
                age_range = user_preference.age.split('-')
                if len(age_range) == 2:
                    try:
                        min_age = int(age_range[0])
                        max_age = int(age_range[1])
                        filter_query &= Q(age__gte=min_age, age__lte=max_age)
                    except ValueError:
                        pass


            # Religion
            if user_preference.religion:
                filter_query &= Q(religion=user_preference.religion)

            # Country
            if user_preference.country_living:
                filter_query &= Q(country=user_preference.country_living)

            # Qualification (M2M)
            if user_preference.qualification.exists():
                filter_query &= Q(qualification__in=user_preference.qualification.all())

            # Occupation (M2M)
            if user_preference.occupation.exists():
                filter_query &= Q(occupation__in=user_preference.occupation.all())

            # Annual Income
            if user_preference.annual_income:
                filter_query &= Q(annual_income__gte=user_preference.annual_income)

            # Marital Status
            if user_preference.marital_status:
                filter_query &= Q(marital_status=user_preference.marital_status)

            # Height
            if user_preference.height:
                try:
                    hmin, hmax = [int(x) for x in user_preference.height.replace('cm', '').split('-')]
                    filter_query &= Q(height__range=(hmin, hmax))
                except ValueError:
                    pass

            # Weight
            if user_preference.weight:
                try:
                    wmin, wmax = [int(x) for x in user_preference.weight.replace('Kg', '').split('-')]
                    filter_query &= Q(weight__range=(wmin, wmax))
                except ValueError:
                    pass

            # Smoke
            if user_preference.smoke:
                filter_query &= Q(smoke=user_preference.smoke)

            # Drink
            if user_preference.drink:
                filter_query &= Q(drink=user_preference.drink)

            # Community
            if user_preference.community:
                filter_query &= Q(caste=user_preference.community)

            # Complexion
            if user_preference.complexion:
                filter_query &= Q(complexion=user_preference.complexion)

        return filter_query

    @staticmethod
    def generate_user_filter_query(filter_data:dict):
        filter_query = Q()
        if 'age' in filter_data:
            age_range = filter_data['age'].split('-')
            if len(age_range) == 2:
                try:
                    min_age = int(age_range[0])
                    max_age = int(age_range[1])
                    filter_query &= Q(age__range=(min_age, max_age))
                except ValueError:
                    pass
        if 'height' in filter_data:
            height_range = filter_data['height'].split('-')
            if len(height_range) == 2:
                try:
                    min_height = int(height_range[0].replace('cm', ''))
                    max_height = int(height_range[1].replace('cm', ''))
                    filter_query &= Q(height__range=(min_height, max_height))
                except ValueError:
                    pass
        
        if 'weight' in filter_data:
            weight_range = filter_data['weight'].split('-')
            if len(weight_range) == 2:
                try:
                    min_weight = int(weight_range[0].replace('Kg', ''))
                    max_weight = int(weight_range[1].replace('Kg', ''))
                    filter_query &= Q(weight__range=(min_weight, max_weight))
                except ValueError:
                    pass
        
        if "joining_period" in filter_data:
            joining_period = filter_data['joining_period']
            if joining_period == const.WITHIN_A_DAY:
                filter_query &= Q(created_at__gte=F('joining_date') - timedelta(days=1))
            elif joining_period == const.WITHIN_A_WEEK:
                filter_query &= Q(created_at__gte=F('joining_date') - timedelta(weeks=1))
            elif joining_period == const.WITHIN_A_MONTH:
                filter_query &= Q(created_at__gte=F('joining_date') - timedelta(days=30))
        
        if 'last_active' in filter_data:
            last_active = filter_data['last_active']
            if last_active == const.WITHIN_A_DAY:
                filter_query &= Q(last_login__gte=now() - timedelta(days=1))
            elif last_active == const.WITHIN_A_WEEK:
                filter_query &= Q(last_login__gte=now() - timedelta(weeks=1))
            elif last_active == const.WITHIN_A_MONTH:
                filter_query &= Q(last_login__gte=now() - timedelta(days=30))
        
        if 'plan_access' in filter_data:
            pass # Placeholder for plan access filter, to be added later

        if 'verification_status' in filter_data:
            verification_status = filter_data['verification_status']
            filter_query &= Q(verification_type=verification_status)
        
        if 'photo_settings' in filter_data:
            photo_settings = filter_data['photo_settings']
            if photo_settings == const.VISIBLE_TO_ALL:
                filter_query &= Q(albums__isnull=False)
            elif photo_settings == const.WITHOUT_PHOTO:
                filter_query &= Q(albums__isnull=True)
            elif photo_settings == const.PROTECTED_PHOTO:
                filter_query &= Q(albums__is_private=True)

        if 'annual_income' in filter_data:
            annual_income = filter_data['annual_income']
            filter_query &= Q(annual_income__id=annual_income)
        
        if "community" in filter_data:
            community = filter_data['community']
            filter_query &= Q(sub_religion__id=community)
        
        if 'nationality' in filter_data:
            nationality = filter_data['nationality']
            filter_query &= Q(country__id=nationality)
        
        if 'state' in filter_data:
            state = filter_data['state']
            filter_query &= Q(city__id=state)
        
        if 'city' in filter_data:
            city = filter_data['city']
            filter_query &= Q(place__id=city)
        
        if 'marital_status' in filter_data:
            marital_status = filter_data['marital_status']
            filter_query &= Q(marital_status__id=marital_status)
        
        if 'family_status' in filter_data:
            family_status = filter_data['family_status']
            filter_query &= Q(family_status__id=family_status)
        
        if 'family_type' in filter_data:
            family_type = filter_data['family_type']
            filter_query &= Q(family_type__id=family_type)
        
        if 'financial_status' in filter_data:
            pass #need to add

        if 'body_type' in filter_data:
            body_type = filter_data['body_type']
            filter_query &= Q(body_type__id=body_type)

        if 'qualification' in filter_data:
            qualification = filter_data['qualification']
            filter_query &= Q(qualification__id=qualification)

        if 'education' in filter_data:
            pass

        if 'profession' in filter_data:
            profession = filter_data['profession']
            filter_query &= Q(occupation__id=profession)

        return filter_query
    
    def user_query_for_matches(user):
        users_data = Users.objects.all().exclude(id=user.id).exclude(gender=user.gender).\
            annotate(full_name=Concat('first_name','last_name'),age_str=Concat(F('age'), \
                Value('yrs'))).select_related(
                    'religion', 'country', 'qualification', 'occupation', 
                    'annual_income', 'diet', 'smoking', 'drinking','sub_religion','country',\
                    'city','place','body_type'
                ).prefetch_related('sessions','account_verifications','albums')
        feet,remaining_inches = Utils.height_to_inches()
        users_data = users_data.annotate(height_formatted=Concat(
                            Cast(feet, CharField()), Value("'"),
                            Cast(Round(remaining_inches), CharField()), Value('"')
                        ),last_login=Max('sessions__created'),verification_type=Value('account_verifications__type'))
        return users_data

    def get_user_data(user_data,fields):
        response = {}
        for field in fields:
            response[field] = None
            if user_data and user_data[0][field]:
                response[field] = user_data[0][field]
        return response
    
    def get_intereset_and_personality_data(user):
        intereset_ids = UsersInterests.objects.filter(user=user).select_related('interest').values_list('interest__id',flat=True)
        personality_ids = UsersPersonality.objects.filter(user=user).select_related('personality').values_list('personality__id',flat=True)
        response = {
            "personality" : personality_ids,
            "interest" : intereset_ids
        }
        return response
    
    def get_partner_preference(user):
        fields = const.PARTNER_PREFERENCE_FIELDS
        partner_data = UserPartnerPreference.objects.filter(user=user).values(*fields)
        response = {}
        for field in fields:
            response[field] = None
            if partner_data and partner_data[0][field]:
                response[field] = partner_data[0][field]
        return response

    def get_onboarding_data(step,platform,user):
        response = {}
        fields = const.BASIC_INFO_FIELDS
        if step == const.STEP_BASIC_INFO:
            user_data = Users.objects.filter(id=user.id).values(*fields)
            response["basic_info_data"] = Utils.get_user_data(user_data=user_data,fields=fields)
            if platform == const.PLATFORM_WEB:
                response["personality"],response["interest"] = Utils.\
                    get_intereset_and_personality_data(user=user)["personality"],\
                    Utils.\
                    get_intereset_and_personality_data(user=user)["interest"]

        elif step == const.STEP_INTERESTS:
            response["interest"] = Utils.get_intereset_and_personality_data(user=user)["interest"]
        elif step == const.STEP_PERSONALITY:
            response["personality"] = Utils.get_intereset_and_personality_data(user=user)["personality"]
        elif step == const.STEP_PHYSICAL_MARITAL_STATUS:
            fields = const.PHYSICAL_MARITAL_STATUS_FIELDS
            user_data = Users.objects.filter(id=user.id).values(*fields)
            response["physical_marital_data"] = Utils.get_user_data(user_data=user_data,fields=fields)
        elif step == const.STEP_CAREER_DETAILS:
            fields = const.CAREER_FIELDS
            user_data = Users.objects.filter(id=user.id).values(*fields)
            response["career_data"] = Utils.get_user_data(user_data=user_data,fields=fields)
        elif step == const.STEP_PARTNER_PREFERENCE:
            response["partner_preference"] = Utils.get_partner_preference(user=user)
        
        return response

    @staticmethod
    def prepare_album_data(request):
        has_error = False
        message = ""
        user_photos_data = []
        profile_image = request.FILES.get('profile_image')
        user_photos = request.FILES.getlist('user_photos')
        is_private = request.data.get("is_private")

        if not profile_image or not isinstance(profile_image, InMemoryUploadedFile):
            has_error = True
            message = const.PRIMARY_PHOTO_REQUIRED

        #Add 1 for primary foto and compare
        if len(user_photos) + 1 > const.PROFILE_PHOTO_UPLOAD_LIMIT:
            has_error = True
            message = const.MAX_PHOTO_LIMIT_EXCEEDED
            
        if not has_error:
            user_photos_data.append({
                'user': request.user.id,
                'image': profile_image,
                'primary': UserAlbum.PrimaryphotoChoices.YES,
                'is_private': is_private
            })

            if user_photos:
                for photo in user_photos:
                    if isinstance(photo, InMemoryUploadedFile):
                        user_photos_data.append({
                            'user': request.user.id,
                            'image': photo,
                            'primary': UserAlbum.PrimaryphotoChoices.NO,
                            'is_private': is_private
                        })
        response = {
            "has_error" : has_error,
            "message" : message,
            "user_photo_data" : user_photos_data
        }

        return response
    
    @staticmethod
    def generate_user_interest_payload(request):
        try:
            user = request.user
            intereset_ids = request.data.get('interests', [])

            current_interests = list(
                UsersInterests.objects.filter(
                    user=user,
                    is_deleted=False
                ).values_list('interest_id', flat=True)
            )
            print(current_interests,"current_interests")

            data_to_delete = list(set(current_interests) - set(intereset_ids))

            data_to_add = list(set(intereset_ids) - set(current_interests))
            created_interests = []
            if data_to_delete:
                UsersInterests.objects.filter(
                user=user,
                interest_id__in=data_to_delete, 
                is_deleted=False
            ).update(is_deleted=True)

            if data_to_add:
            
                for interest_id in data_to_add: 
                    data={
                        "interest" :interest_id ,
                        "user" : request.user.id               
                    }
                
                    created_interests.append(data)  
            return {
                "interest_data": created_interests  
            }

        except Exception as e:
            return {
                "has_error": True,
                "message": str(e)
            }
    
    
    @staticmethod
    def generate_user_personality_payload(request):
        try:
            user = request.user
            personality_ids = request.data.get('personality', [])
 
            current_personalities = list(
                UsersPersonality.objects.filter(
                    user=user,
                    is_deleted=False
                ).values_list('personality_id', flat=True)
            )
            print(current_personalities,"current_personalities")
 
            data_to_delete = list(set(current_personalities) - set(personality_ids))
 
            data_to_add = list(set(personality_ids) - set(current_personalities))
            if data_to_delete:
                UsersPersonality.objects.filter(
                user=user,
                personality_id__in=data_to_delete,
                is_deleted=False
            ).update(is_deleted=True)
            created_personalities = []
            if data_to_add:
               
                for personality_id in data_to_add:
                    data={
                        "personality" :personality_id ,
                        "user" : request.user.id              
                    }
               
                    created_personalities.append(data)  
            return {
                "personality_data": created_personalities  
            }
 
        except Exception as e:
            return {
                "has_error": True,
                "message": str(e)
            }

    
    @staticmethod
    def check_basic_info_exists(data):
        required_fields = ['dob','religion','sub_religion','country','city','town','place']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return error_(
                message=f"Required fields are missing: {', '.join(missing_fields)}",
                response={"missing_fields": missing_fields}
            )
        return None
    

    @staticmethod
    def update_user_images(request):
        has_error = False
        message = ""
        user_photos_data = []
        image_count = 0

        set_as_primary_id = request.data.get('set_as_primary_id_id',None)
        removed_ids = ast.literal_eval(request.data.get('removed_ids',[]))
        files = request.FILES.getlist('files')
        primary_photo = request.FILES.get('primary_photo')
        is_private = request.data.get('is_private')

        user_album_ids = list(UserAlbum.objects.filter(is_deleted=False,user=request.user).values_list('id',flat=True))
        image_count += len(list(set(user_album_ids+removed_ids)))
        image_count += len(files)
        image_count+= 1 if primary_photo else 0

        if removed_ids:
            if UserAlbum.objects.filter(user=request.user,id__in=removed_ids,is_deleted=False,\
                        primary=UserAlbum.PrimaryphotoChoices.YES).exists():
                if not set_as_primary_id and not primary_photo:
                    has_error = True
                    message = const.PRIMARY_PHOTO_REQUIRED
            UserAlbum.objects.filter(id__in=removed_ids,is_deleted=False,user=request.user).update(is_deleted=True)

        if image_count > const.PROFILE_PHOTO_UPLOAD_LIMIT:
            has_error = True
            message = const.MAX_PHOTO_LIMIT_EXCEEDED

        if set_as_primary_id:
            UserAlbum.objects.filter(id=set_as_primary_id,is_deleted=False,user=request.user).update(primary=UserAlbum.PrimaryphotoChoices.YES)
            
        if not has_error:
            if primary_photo:
                user_photos_data.append({
                    'user': request.user.id,
                    'image': primary_photo,
                    'primary': UserAlbum.PrimaryphotoChoices.YES,
                    'is_private': is_private
                })

            if files:
                for photo in files:
                    if isinstance(photo, InMemoryUploadedFile):
                        user_photos_data.append({
                            'user': request.user.id,
                            'image': photo,
                            'primary': UserAlbum.PrimaryphotoChoices.NO,
                            'is_private': is_private
                        })
        response = {
            "has_error" : has_error,
            "message" : message,
            "user_photo_data" : user_photos_data
        }

        return response
