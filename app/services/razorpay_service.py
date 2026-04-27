import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
        )

    def create_order(self, amount: int, currency: str = "INR"):
        """
        Creates a Razorpay order.
        Amount should be in paise (e.g., 10000 for ₹100).
        """
        data = {
            "amount": amount,
            "currency": currency,
            "payment_capture": 1 # Auto-capture payment
        }
        return self.client.order.create(data=data)

    def verify_signature(self, params_dict: dict):
        """
        Verifies the Razorpay payment signature.
        params_dict: {razorpay_order_id, razorpay_payment_id, razorpay_signature}
        """
        try:
            return self.client.utility.verify_payment_signature(params_dict)
        except Exception:
            return False
