@shared_task
def send_notification(user, message):
    push_notification = OloAdminSettings.objects.filter(key='turn_on_push_notification').first()
    if push_notification and push_notification.value not in ['True', 'true']:
        return None
       
    #send a notification to a single user
    firebase_service = FirebaseNotificationService()    
    user = User.objects.get(id=user)  # Ensure user is fetched from the database
    user_sessions = user.sessions.filter(is_active=True)
    tokens = list(set(
        session.push_token.strip()
        for session in user_sessions
        if session.push_token and session.push_token.strip()
    ))
    print(tokens)
    if not tokens:
        return {"success": False, "error": "No active push tokens found for user."}
    firebase_service.send_to_multiple_users(
        tokens=tokens,
        title=message.get("title", "Notification"),
        body=message.get("body", message.get("title", "You have a new notification")),
        data=message.get("data", {})
    )
    return {"success": True, "message": "Notification sent to user."}
 
@shared_task
def save_customer_notification(data):
    """
    Save a customer notification in the database and trigger push notification.
 
    Expected `data` format:
    {
        'type': '1' | '2' | '3',  # GARAGEDETAIL | GENERAL | BOOKING
        'title': <str>,
        'body': <str>,
        'link_to': <int>,        # ID of booking or garage
    }
    """
    try:
        customer = None
        vehicle = None
        expiry_date = timezone.now().date() + timedelta(days=1)  # Default
 
        if data['notification_type'] == CustomerNotification.NotificationType.BOOKING:
            booking = Booking.objects.get(pk=data['link_to'])
            customer = booking.customer
            expiry_date = booking.date + timedelta(days=1) if booking.date else expiry_date
            vehicle = booking.customer_vehicle
        elif data['notification_type']  ==CustomerNotification.NotificationType.VEHICLE:
            vehicle = CustomerVehicle.objects.get(pk=data['link_to'])
            customer = vehicle.customer  
        elif data['notification_type']  ==CustomerNotification.NotificationType.GENERAL:
            customer = Customer.objects.get(pk=data['link_to'])  
        else:
            # You can optionally support other types here
            logger.warning("Non-booking notification received without customer. Skipping.")
            return False
       
        notification_data = {
            "link_to": str(data['link_to']),
            "notification_type": str(data['notification_type']),
            "user_id":str(customer.user.id),
            "vehicle_id":str(vehicle.id) if vehicle else ''
        }
        # Create the notification in DB
        notification = CustomerNotification.objects.create(
            customer=customer,
            type=data['notification_type'],
            title=data['title'],
            message_content=data['body'],
            link_to=data['link_to'],
            expiry_date=expiry_date,
            status=CustomerNotification.StatusType.ACTIVE,
            data = notification_data
        )
        # Send FCM push notification
        notification_setting = OloAdminSettings.objects.filter(key='turn_on_push_notification').first()
        if notification_setting and str(notification_setting.value).lower() in ['true', '1']:
            send_notification.delay(customer.user.id, {
                "title": str(notification.title),
                "body": str(notification.message_content),
                "data": notification_data
            })
        return True
    except Booking.DoesNotExist:
        logger.error(f"Booking not found with id={data.get('booking_id')}")
        return False
 
    except Exception as e:
        logger.exception("Unexpected error while saving customer notification")
        return False
 
@shared_task
def save_merchant_notification(data):
    """
    Save a merchant notification in the database and trigger push notification.
 
    Expected `data` format:
    {
        'notification_type': '1' | '2' | '3' | '4',  # Enum value
        'title': <str>,
        'body': <str>,
        'link_to': <int>,
    }
    """
    try:
        merchant = None
        garage = None
        expiry_date = timezone.now().date() + timedelta(days=1)
 
        notification_type = data['notification_type']
 
        # BOOKING notification
        if notification_type == MerchantNotification.NotificationType.BOOKING:
            booking = Booking.objects.get(pk=data['link_to'])
            garage = booking.garage
            merchant = garage.merchants.first()
            expiry_date = booking.date + timedelta(days=1) if booking.date else expiry_date
 
        # SERVICE notification
        elif notification_type == MerchantNotification.NotificationType.SERVICE:
            # service = Service.objects.get(pk=data['link_to'])
            # garage_service = GarageService.objects.filter(service=service).first()
            # if not garage_service:
            #     logger.warning("GarageService not found for service")
            #     return False
            garage = Garage.objects.get(pk=data['garage_id'])
            merchant = garage.merchants.first()
 
        # PACKAGE notification
        elif notification_type == MerchantNotification.NotificationType.PACKAGE:
            package = Package.objects.get(pk=data['link_to'])
            garage = Garage.objects.get(pk =data['garage_id'])
            merchant = garage.merchants.first()
 
        # WALLET notification (direct merchant)
        elif notification_type == MerchantNotification.NotificationType.WALLET:
            merchant = Merchant.objects.get(pk=data['link_to'])
        elif notification_type == MerchantNotification.NotificationType.GENERAL:
            merchant=Merchant.objects.get(pk=data['link_to'])
        else:
            logger.warning(f"Unsupported notification type: {notification_type}")
            return False
 
        if not merchant:
            logger.warning("Merchant not found.")
            return False
 
        # Prepare notification data
        notification_data = {
            "link_to": str(data['link_to']),
            "notification_type": str(notification_type),
            "user_id": str(merchant.user.id),
            "garage_id": str(garage.id) if garage else ''
        }
 
        # Create merchant notification
        notification = MerchantNotification.objects.create(
            merchant=merchant,
            notification_type=notification_type,
            title=data['title'],
            message_content=data['body'],
            link_to=data['link_to'],
            expiry_date=expiry_date,
            status=MerchantNotification.StatusType.ACTIVE,
            data=notification_data
        )
 
        # Send Firebase push notification
        notification_setting = OloAdminSettings.objects.filter(key='turn_on_push_notification').first()
        if notification_setting and str(notification_setting.value).lower() in ['true', '1']:
            send_notification.delay(merchant.user.id, {
                "title": str(notification.title),
                "body": str(notification.message_content),
                "data": notification_data
            })
        return True
 
    except Booking.DoesNotExist:
        logger.error(f"Booking not found with id={data.get('link_to')}")
        return False
    except Service.DoesNotExist:
        logger.error(f"Service not found with id={data.get('link_to')}")
        return False
    except Package.DoesNotExist:
        logger.error(f"Package not found with id={data.get('link_to')}")
        return False
    except Merchant.DoesNotExist:
        logger.error(f"Merchant not found with id={data.get('link_to')}")
        return False
    except Exception as e:
        logger.exception("Unexpected error while saving merchant notification")
        return False
   
@shared_task    
def send_notification_to_all_merchant(data):
   
    push_notification = OloAdminSettings.objects.filter(key='turn_on_push_notification').first()
    if push_notification and push_notification.value not in ['True', 'true']:
        return None    
   
    try:
        merchants = User.objects.filter(
            user_status=User.StatusType.ACTIVE,
            user_type=UserChoice.MERCHANT
        )
        firebase_service = FirebaseNotificationService()
        tokens = []  
        for user in merchants:
            user_sessions = user.sessions.filter(is_active=True)
            user_tokens = [session.push_token for session in user_sessions if session.push_token]
            tokens.extend(user_tokens)  # Add all valid tokens to the main list
 
            notification_data = {
                "link_to": str(data['link_to']),
                "notification_type": str(data['notification_type']),
                "user_id":str(user.id),
            }
            merchant = Merchant.objects.filter(user_id=user.id).first()
            notification = MerchantNotification.objects.create(
                merchant=merchant,
                notification_type=data['notification_type'],
                title=data['title'],
                message_content=data['body'],
                link_to=data['link_to'],
                expiry_date = timezone.now().date() + timedelta(days=1),
                status=MerchantNotification.StatusType.ACTIVE,
                data = notification_data
            )
        if not tokens:
                return {"success": False, "error": "No active push tokens found for any user."}
        # Now send notification to all tokens
        firebase_service.send_to_multiple_users(
            tokens=tokens,
            title=data.get("title", "Notification"),
            body=data.get("body", data.get("title", "You have a new notification")),
            data=data.get("data", {})
        )
 
    except Exception as e:
        logger.exception("Unexpected error while saving mecrhant notification")
        return False
 
@shared_task(bind=True)
def send_customer_email(self, to_email, subject, template_name, context):
    try:
        html_content = render_to_string(f'emails/customer/{template_name}', context)
        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    except Exception as e:
        logger.exception(f"Failed to send customer email to {to_email}: {e}")
        return False  # Or just silently fail if that's desired
@shared_task(bind=True)
def send_merchant_email(self, to_email, subject, template_name, context):
    try:
        html_content = render_to_string(f'emails/merchant/{template_name}', context)
        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    except Exception as e:
        logger.exception(f"Failed to send merchant email to {to_email}: {e}")
        return False
   
def expire_old_notifications():
    try:
        today = timezone.now().date()
        #customer
        CustomerNotification.objects.filter(
            expiry_date__lte=today,
            status=CustomerNotification.StatusType.ACTIVE
        ).update(
            status=CustomerNotification.StatusType.EXPIRED,
        )
        # merchant
        MerchantNotification.objects.filter(
            expiry_date__lte=today,
            status= MerchantNotification.StatusType.ACTIVE  
        ).update(
            status=MerchantNotification.StatusType.EXPIRED,
        )
    except Exception as e:
        logger.exception(f"Failed to expire notifications: {e}")
        return False
   
 
