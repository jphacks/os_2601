export type ErrorCode =
  | "BAD_REQUEST"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "STATE_CONFLICT"
  | "FRAME_TOO_LARGE"
  | "VALIDATION_ERROR"
  | "RATE_LIMITED"
  | "INTERNAL"
  | "HINT_UNAVAILABLE";

export type ApiErrorBody = { error: { code: ErrorCode; message: string } };

export class ApiError extends Error {
  readonly status: number;
  readonly code: ErrorCode | "UNKNOWN";

  constructor(status: number, code: ErrorCode | "UNKNOWN", detail = "") {
    super(detail ? `API ${status} ${code}: ${detail}` : `API ${status} ${code}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  static async fromResponse(response: Response): Promise<ApiError> {
    const body: ApiErrorBody | null = await response.json().catch(() => null);
    return new ApiError(response.status, body?.error?.code ?? "UNKNOWN", body?.error?.message);
  }
}
