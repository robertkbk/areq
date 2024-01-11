from typing import Literal, TypedDict


class ResponseBase(TypedDict):
    tag: str | None


class SubmitResponse(ResponseBase):
    status: Literal["QUEUED", "FINISHED"]
    job_id: str
    stdout_path: str
    stderr_path: str


class Error(ResponseBase):
    status: Literal["ERROR"]
    exit_code: int
    standard_output: str
    error_output: str
    error_message: str
