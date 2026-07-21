import re
import sys


class ConsoleSmsGateway:
    def send(self, to: str, body: str) -> bool:
        otp_match = re.search(r"\b(\d{6})\b", body)
        otp_hint = f"   OTP: {otp_match.group(1)}" if otp_match else ""
        print(f"\U0001F4F1 SMS to {to}: \"{body}\"", file=sys.stdout)
        if otp_hint:
            print(otp_hint, file=sys.stdout)
        return True
