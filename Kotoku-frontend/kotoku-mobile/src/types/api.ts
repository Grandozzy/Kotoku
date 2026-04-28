export interface ApiResponse<T> {
  status: "ok" | "error";
  data: T;
}

export interface ApiError {
  status: "error";
  message: string;
  code?: string;
}
