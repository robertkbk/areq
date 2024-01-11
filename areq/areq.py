import os
from collections.abc import Sequence
from typing import Literal, TypeAlias

import requests
import urllib.parse

from .options import Options, to_sbatch_options
from .response import Error, SubmitResponse

Hosts: TypeAlias = Literal["ares.cyfronet.pl"]


def _build_script(lines: Sequence[str], options: Options, shebang: str | None) -> str:
    if lines[0].startswith("#!"):
        shebang = lines[0]

    else:
        if shebang is None:
            raise ValueError(
                "Interpreter not specified! "
                "Either specify shebang in script or select interpreter"
            )

        shebang = shebang

    return "\n".join([shebang, *to_sbatch_options(options), *lines[1:]])


class Areq:
    _BASE_URL = "https://submit.plgrid.pl/api/"

    def __init__(
        self,
        proxy_path: str | bytes | os.PathLike,
        host: Hosts = "ares.cyfronet.pl",
        interpreter: str | None = "/bin/sh",
    ) -> None:
        self._host = host

        if interpreter is None:
            self._shebang = None
        else:
            self._shebang = (
                interpreter if interpreter.startswith("#!") else f"#!{interpreter}"
            )

        with open(proxy_path, "rb") as proxy_file:
            proxy = proxy_file.read()
            proxy = base64.encodebytes(proxy)
            proxy = proxy.replace(b"\n", b"")

        self._proxy = proxy

    def _request(
        self, method: str, path: str, *, headers: dict[str, str] | None = None, **kwargs
    ) -> requests.Response:
        return requests.request(
            method,
            self._BASE_URL + path,
            headers={**(headers or {}), "PROXY": self._proxy},
            **kwargs,
        )

    def submit(
        self,
        script: str,
        options: Options,
        working_directory: str | bytes | os.PathLike | None = None,
    ) -> SubmitResponse | Error:
        if len(lines := script.strip().splitlines()) == 0:
            raise ValueError("script is empty")

        body: dict[str, object] = {
            "host": self._host,
            "script": _build_script(lines, options, self._shebang),
        }

        if working_directory is not None:
            body["working_directory"] = working_directory

        response = self._request("POST", "jobs", json=body)
        return response.json()

    def statuses(
        self,
        job_id: str | list[str],
        tag: str | None = None,
        format: str | None = None,
    ) -> list[SubmitResponse] | Error:
        response = self._request(
            "GET", "jobs", params={"job_id": job_id, "tag": tag, "format": format}
        )
        return response.json()

    def status(self, job_id: str) -> SubmitResponse | Error:
        id_quoted = urllib.parse.quote(job_id)
        response = self._request("GET", f"jobs/{id_quoted}")
        return response.json()

    def delete(self, job_id: str) -> Error | None:
        id_quoted = urllib.parse.quote(job_id)
        response = self._request("DELETE", f"jobs/{id_quoted}")

        if not response.ok:
            return response.json()

    def abort(self, job_id: str) -> Error | None:
        id_quoted = urllib.parse.quote(job_id)
        response = self._request("PUT", f"jobs/{id_quoted}", json={"action": "abort"})

        if not response.ok:
            return response.json()
