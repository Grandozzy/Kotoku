import { Amplify } from "aws-amplify";

Amplify.configure({
  Auth: {
    Cognito: {
      identityPoolId: "eu-west-1:869e47c6-53c0-4dbc-9379-bcae17769346",
      allowGuestAccess: true,
    },
  },
});
