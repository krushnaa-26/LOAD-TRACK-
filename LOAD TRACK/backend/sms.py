import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("loadtrack.sms")

def send_challan_sms(phone_number, message):
    """
    Sends an SMS notification via Twilio SDK or falls back to a simulated console SMS.
    
    Args:
        phone_number (str): Recipient phone number (e.g. +919820012345)
        message (str): SMS text content
        
    Returns:
        dict: Status detailing whether real SMS was sent or simulated
    """
    twilio_sid = os.getenv("TWILIO_SID", "").strip()
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio_from = os.getenv("TWILIO_FROM_NUMBER", "").strip()

    # Check if credentials exist and are not default placeholders
    has_valid_credentials = (
        twilio_sid and 
        twilio_auth_token and 
        twilio_from and 
        not twilio_sid.startswith("ACXXXX") and 
        "your_" not in twilio_auth_token
    )

    if has_valid_credentials:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_auth_token)
            sent_message = client.messages.create(
                body=message,
                from_=twilio_from,
                to=phone_number
            )
            logger.info(f"[TWILIO REAL SMS SENT] SID: {sent_message.sid} To: {phone_number}")
            return {
                "sent": True,
                "mode": "real_twilio",
                "sid": sent_message.sid,
                "recipient": phone_number,
                "message": message
            }
        except Exception as e:
            logger.warning(f"[TWILIO ERROR - FALLING BACK TO SIMULATED SMS] Error: {str(e)}")

    # Fallback / Simulated SMS Mode
    simulated_log = f"\n" + "="*70 + f"\n[SIMULATED SMS DISPATCH]\nTO: {phone_number}\nMESSAGE:\n{message}\n" + "="*70
    print(simulated_log)
    logger.info(f"[SIMULATED SMS] Sent to {phone_number}")
    
    return {
        "sent": True,
        "mode": "simulated",
        "recipient": phone_number,
        "message": message
    }
