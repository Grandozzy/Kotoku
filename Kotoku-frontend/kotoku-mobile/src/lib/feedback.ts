import { Platform, Vibration } from "react-native";

function vibrate(pattern: number | number[]) {
  if (Platform.OS === "web") return;
  Vibration.vibrate(pattern);
}

export function feedbackSuccess() {
  vibrate(35);
}

export function feedbackAction() {
  vibrate(15);
}

export function feedbackWarning() {
  vibrate([0, 30, 40, 30]);
}
