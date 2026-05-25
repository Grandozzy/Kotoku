from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class AuthIpRateThrottle(AnonRateThrottle):
    scope = "auth_ip"


class RefreshIpRateThrottle(AnonRateThrottle):
    scope = "refresh_ip"


class _PhoneRateThrottle(SimpleRateThrottle):
    phone_field = "phone"

    def get_cache_key(self, request, view):
        phone = request.data.get(self.phone_field, "")
        if not phone:
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(request),
            }
        return self.cache_format % {
            "scope": self.scope,
            "ident": phone.strip(),
        }


class SendOtpPhoneRateThrottle(_PhoneRateThrottle):
    scope = "send_otp_phone"


class VerifyOtpPhoneRateThrottle(_PhoneRateThrottle):
    scope = "verify_otp_phone"


class PinVerifyPhoneRateThrottle(_PhoneRateThrottle):
    scope = "pin_verify_phone"
