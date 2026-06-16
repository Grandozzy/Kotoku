declare module "react-native-sms-user-consent" {
  interface SMSMessage {
    receivedOtpMessage: string;
  }

  const SMSUserConsent: {
    listenOTP(): Promise<SMSMessage>;
    removeOTPListener(): void;
  };

  export default SMSUserConsent;
}
