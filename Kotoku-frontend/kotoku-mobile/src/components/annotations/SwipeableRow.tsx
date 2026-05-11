import { ReactNode, useRef } from "react";
import { Animated, Pressable, View } from "react-native";
import { Swipeable } from "react-native-gesture-handler";
import { Pencil, Trash2 } from "lucide-react-native";

interface SwipeableRowProps {
  children: ReactNode;
  onDelete: () => void;
  onEdit: () => void;
  note: unknown;
  disabled?: boolean;
}

export function SwipeableRow({ children, onDelete, onEdit, note, disabled }: SwipeableRowProps) {
  const swipeableRef = useRef<Swipeable>(null);

  const renderLeftActions = (
    _progress: Animated.AnimatedInterpolation<number>,
    _dragX: Animated.AnimatedInterpolation<number>,
  ) => {
    return (
      <Pressable
        onPress={() => {
          swipeableRef.current?.close();
          onEdit();
        }}
        className="bg-blue-600 justify-center items-center w-20"
      >
        <Pencil size={24} color="white" />
      </Pressable>
    );
  };

  const renderRightActions = (
    _progress: Animated.AnimatedInterpolation<number>,
    _dragX: Animated.AnimatedInterpolation<number>,
  ) => {
    return (
      <Pressable
        onPress={() => {
          swipeableRef.current?.close();
          onDelete();
        }}
        className="bg-red-600 justify-center items-center w-20"
      >
        <Trash2 size={24} color="white" />
      </Pressable>
    );
  };

  if (disabled) {
    return <>{children}</>;
  }

  return (
    <Swipeable
      ref={swipeableRef}
      renderLeftActions={renderLeftActions}
      renderRightActions={renderRightActions}
      leftThreshold={40}
      rightThreshold={40}
      overshootRight={false}
      overshootLeft={false}
    >
      {children}
    </Swipeable>
  );
}