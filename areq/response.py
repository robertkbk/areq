from typing import TypedDict


class ResponseBase(TypedDict):
    status: str
    tag: str | None


class SubmitResponse(ResponseBase):
    job_id: str
    stdout_path: str
    stderr_path: str


class Error(ResponseBase):
    exit_code: int
    standard_output: str
    error_output: str
    error_message: str
