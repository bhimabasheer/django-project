import re
from rest_framework import serializers
from click_for_marry import constants as const
from django.core.paginator import Paginator
import logging
import re
import uuid
from datetime import datetime, timedelta, date
import pytz
from django.db.models import Q
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from user_agents import parse
from django.db.models.expressions import Func

""" CLASS TO HANDLE UTILITY FUNCTIONS """
class Utils:

    @staticmethod
    def get_client_ip(request):
        """Extracts client IP from request, handling proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')

    @staticmethod
    def get_device_id(request):
        """Extracts device ID from headers > body > generates UUID"""
        return (
            request.headers.get('X-Device-ID') 
            or request.data.get('device_id') 
            or str(uuid.uuid4())
        )

    @staticmethod
    def get_user_data(user):
        """Standardized user data response"""
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "aec_id": user.aec_id,
            "is_premium_member" : user.is_premium_member,
            "is_new_user" : not user.activity_created_user.exists(),
            "onboarding_steps" : user.onboarding_steps + 1,
            "name" : f"{user.first_name} {user.last_name}",
            "gender" : user.gender.name if user.gender else None
        }
        # onboarding_step = user.onboarding_steps + 1

        # if (onboarding_step and onboarding_step != 0) or (onboarding_step == 0):
        #     onboarding_step=user.onboarding_steps
        # elif onboarding_step == const.STEP_PHOTOS_UPLOADED:
        #     onboarding_step = const.ONBOARDING_STEP_COMPLETED
        # else:
        #     onboarding_step = const.STEP_BASIC_INFO
        
        # user_data["onboarding_steps"] = onboarding_step + 1  #give next step number to show next page

        return user_data

    @staticmethod
    def validate_identifier(value: str):
        from users.models import Users
        """Common validation for email/phone identifiers"""
        has_error = False
        message = ""
        email = None
        phone = None
        value = value.strip().lower()

        if Utils.is_valid_email(value):
            email = value
            if Users.objects.filter(Q(email=value) | Q(username=value)).exists():
                has_error = True
                message = const.EMAIL_ALREADY_USED
        else:
            try:
                value = int(value)
                phone = value
                if Users.objects.filter(Q(phone=str(value)) | Q(username=str(value))).exists():
                    has_error = True
                    message = const.PHONE_NUMBER_ALREADY_USED
            except:
                has_error = True
                message = const.IDENTIFIER_NOT_VALID

        return {
            "has_error": has_error,
            "message": message,
            "email": email,
            "phone": phone,
        }
    
    @staticmethod
    def validate_login_identifier(value: str,is_account_creation: bool = False):
        from users.models import Users
        email = None
        phone = None
        aec_id = None
        has_error = False
        message = ""
 
        value = value.strip().lower()
 
        if Utils.is_valid_email(value):
            email = value
        try:
            if not is_account_creation and Users.objects.filter(phone=value).exists():
                phone = value
            elif not is_account_creation and Users.objects.filter(aec_id=value).exists():
                aec_id = value
        except:
            has_error = True
            message = const.IDENTIFIER_NOT_VALID
        return {
            "has_error": has_error,
            "message": message,
            "email": email,
            "phone": phone,
            "aec_id": aec_id
        }

    # pagination functionality
    @staticmethod
    def pagination(
        queryset, page: int=1, limit: int=None):
        
        try:
            if page and limit:
                if queryset:
                    paginator = Paginator(
                        queryset, limit
                    )  # calling django default pagination
                    queryset = paginator.page(page)

        except Exception as e:
            queryset = []
            logging.getLogger("error_logger").error(
                "Pagination error: " + str(e)
            )

        response_data = {"queryset": queryset, "pagination": {}}
        return response_data

    @staticmethod
    def is_valid_email(email: str):
        # regular expression pattern for  email validation
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        regex = re.compile(pattern)

        # use the regex object to match the email address
        if regex.match(email):
            return True
        else:
            return False
        
    @staticmethod
    def get_relative_time(date):
        now = timezone.now()
        diff = now - date
 
        if diff.days > 0:
            if diff.days == 1:
                return "1 day ago"
            return f"{diff.days} days ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            if hours == 1:
                return "1 hr ago"
            return f"{hours} hrs ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            if minutes == 1:
                return "1 min ago"
            return f"{minutes} min ago"
        else:
            return "just now"
    
    @staticmethod
    def get_date_str(date):
        try:
            utc_dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
            utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
            date = utc_dt.strftime("%d %Y, %I:%M%p")  # "July 10, 05:36AM"
        except:
            pass
        return date
    
    @staticmethod
    def validate_otp_time(identifier: str):
        from accounts.models import OTP
        """Common validation for email/phone identifiers"""
        has_error = False
        message = ""
        identifier = str(identifier).strip().lower()
        if OTP.objects.filter(Q(phone=identifier) | Q(email = identifier)).exists():
            latest_otp_data = OTP.objects.filter(Q(phone=identifier) | Q(email = identifier)).last()
            now = timezone.now()

            if now - latest_otp_data.created_at < timedelta(seconds=const.OTP_RESENT_TIME):
                has_error = True
                message = const.OTP_ALREADY_SENT

        return {
            "has_error": has_error,
            "message": message,
        }
    
    @staticmethod
    def validate_create_account_data(data):
        from users.models import Users
        identifier = str(data["identifier"])
        password = str(data["password"])
        confirm_password = str(data["confirm_password"])
        has_error = False
        message = ""

        query = Q(phone=identifier) | Q(email = identifier)
        user_data = Users.objects.filter(query)

        # Verify pre-verified account exists

        if password != confirm_password:
            has_error = True
            message = const.PASSWORD_MISMATCH
            return {
                "has_error": has_error,
                "message": message,
            }
        
        if not user_data.exists():
            has_error = True
            message = const.OTP_VERIFICATION_INCOMPLETE
            return {
                "has_error": has_error,
                "message": message,
            }

        # Check if account already exists with password
        user_data = user_data.last()
        if user_data.password:
            has_error = True
            message = const.PASSWORD_ALREADY_SET
            return {
                "has_error": has_error,
                "message": message,
            }
        
        return {
                "has_error": has_error,
                "message": message,
            }
    
    @staticmethod
    def validate_account_create_identifier(value: str):
        from users.models import Users
        """Common validation for email/phone identifiers"""
        has_error = False
        message = ""
        email = None
        phone = None
        value = value.strip().lower()

        if Utils.is_valid_email(value):
            email = value
        else:
            try:
                value = int(value)
                phone = value
            except:
                has_error = True
                message = const.IDENTIFIER_NOT_VALID

        return {
            "has_error": has_error,
            "message": message,
            "email": email,
            "phone": phone,
        }
    
    @staticmethod
    def extract_validation_error(errors):
        error_msg = ""
        if 'non_field_errors' in errors:
            error_msg = ' '.join([str(msg) for msg in errors['non_field_errors']])
        else:
            # Otherwise, collect all field-specific errors
            error_msgs = []
            for field, messages in errors.items():
                for msg in messages:
                    error_msgs.append(f"{msg}")
            error_msg = ' | '.join(error_msgs)

        return error_msg
    
    @staticmethod
    def validate_dob(dob,user_gender):
        try:
            from common.models import ListValue
            has_error = False
            message = ""
            now = date.today()
            dob = datetime.strptime(dob,const.DATABASE_DATE_TIME_FORMAT).date()
            age = (relativedelta(now, dob)).years
            gender_data = ListValue.objects.filter(id=user_gender).first()
            if gender_data:
                if gender_data.name == const.GENDER_MALE:
                    if age < const.MIN_GENDER_MALE_AGE:
                        has_error = True
                        message = f"You are below the minimum age required for {gender_data.name}"
                else:
                    if age < const.MIN_GENDER_FEMALE_AGE:
                        has_error = True
                        message = f"You are below the minimum age required for {gender_data.name}"
            else:
                has_error = True
                message = "Invalid gender ID"

            return {"has_error": has_error, "message": message}
        except Exception as e:
            print(str(e))
    
    @staticmethod
    def validate_login_with_otp_identifier(value):
        from users.models import Users
        username = None
        has_error = False
        message = const.USER_NOT_EXIST
        is_email = False
        if Utils.is_valid_email(value):
            username = value
            is_email = True
        elif value[:3] == "AEC":
            user_data = Users.objects.filter(aec_id=value)
            if user_data.exists():
                if user_data.last().email:
                    is_email = True
                    username = user_data.last().email
                elif user_data.last().phone:
                    username = user_data.last().phone
                else:
                    has_error = True
                    message = const.USER_NOT_EXIST
            else:
                has_error = True
                message = const.USER_NOT_EXIST
        else:
            try:
                value = int(value)
                username = value
            except:
                has_error = True
                message = const.IDENTIFIER_NOT_VALID
        if not has_error:
            if username:
                if Users.objects.filter(username=username).exists():
                    has_error = False
                else:
                    has_error = True
            else:
                has_error = True
        return {"has_error" : has_error,"message" : message,"is_email" : is_email,"username" :username}
    
    @staticmethod
    def get_login_platform_info(request):
        user_agent_str = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(user_agent_str)

        browser = user_agent.browser.family
        os = user_agent.os.family

        browser_info = f"{browser} ({os})"
        return browser_info
    
    @staticmethod
    def insert_session_data(request,device_id):
        try:
            from users.models import Session
            Session.objects.create(
                    user=request.user,
                    session_id=str(uuid.uuid4()),
                    device_type=int(request.headers.get('X-Platform', const.PLATFORM_WEB)),
                    device_id=device_id,
                    device_name = Utils.get_login_platform_info(request),
                    # location = None, to be saved
                    last_login=timezone.now()
                )
        except Exception as e:
            print("------------Error inserting session data------------",str(e))
            logging.getLogger("error_logger").error(
                "Error inserting session data: " + str(e)
            )
    
    @staticmethod
    def insert_activity_log(visitor_user, visited_user, op, ip_address=None, device_id=None):
        from common.models import Activity
        activity_data = None
        if op == const.PROFILE_VIEWED:
            if Activity.objects.filter(user=visitor_user,op=op,to=visited_user).exists():
                activity_data = Activity.objects.filter(user=visitor_user,op=op,to=visited_user)
                activity_data.update(updated_at=datetime.now())
        if not activity_data:
            Activity.objects.create(
                user=visitor_user,      
                op=op,     
                to=visited_user,           
                ip_address=ip_address,
                device_id=device_id
            )

    @staticmethod
    def calculate_height_in_cm(height_in_feet):
        height_in_feet = height_in_feet.replace("ft","").strip()
        height = 0
        try:
            feet, inches = map(int, height_in_feet.split("."))
            feet, inches = float(feet), float(inches)
            height = ((feet * 12) + inches) * 2.54 
            return height
        except:
            return height
    
    @staticmethod
    def calculate_height_range_in_cm(height_in_feet): #5.6 ft - 5.8 ft format
        height_in_feet = height_in_feet.replace("ft","")
        lower_range, higher_range = map(str, height_in_feet.split("-"))
        height = ""
        try:
            lower_range_feet, lower_range_inches = map(str, lower_range.split("."))
            higher_range_feet, higher_range_inches = map(str, higher_range.split("."))
            lower_range_feet, lower_range_inches = float(lower_range_feet), float(lower_range_inches)
            higher_range_feet, higher_range_inches = float(higher_range_feet), float(higher_range_inches)
            lower_height = ((lower_range_feet * 12) + lower_range_inches) * 2.54 
            higher_height = ((higher_range_feet * 12) + higher_range_inches) * 2.54 
            return f"{round(lower_height)} cm-{round(higher_height)} cm"
        except:
            return height
    
    @staticmethod
    def get_related_object_reponse(obj):
        if obj:
            return {"id" : obj.id,"name" : getattr(obj,"name", None) or getattr(obj, "income", None)}
        else:
            return {}
    
    @staticmethod
    def get_related_object_list_reponse(obj):
        if obj.exists():
            return [{"id" : data.id,"name" :getattr(data,"name", None) or getattr(data, "income", None)} for data in obj.all()]
        else:
            return []
        
    @staticmethod
    def check_notification_enabled(user):
        from common.models import NotificationSettings
        settings_obj = NotificationSettings.objects.filter(user=user)
        for settings in settings_obj:
            if settings.sms != NotificationSettings.SmsEmailPushTypes.OFF or settings.email != NotificationSettings.SmsEmailPushTypes.OFF or\
                  settings.push != NotificationSettings.SmsEmailPushTypes.OFF:
                return True
        return False 
            

class Interval(Func):
    function = ''
    template = "INTERVAL %(expressions)s DAY"
