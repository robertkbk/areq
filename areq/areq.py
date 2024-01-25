import base64
import os
from collections.abc import Sequence
from typing import Literal, TypeAlias

import requests
import urllib.parse
import paramiko
import urllib.parse

from options import Options, to_sbatch_options
from response import Error, SubmitResponse

Hosts: TypeAlias = Literal["ares.cyfronet.pl"]


class SSHException(Exception):
    ...


class AreqException(Exception):
    ...


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
        username: str,
        proxy_path: str | bytes | os.PathLike | None = None,
        host: Hosts = "ares.cyfronet.pl",
        interpreter: str | None = "/bin/sh",
        pkey_path: str | None = None,
        password: str | None = None,
    ) -> None:
        if interpreter is None:
            self._shebang = None
        else:
            self._shebang = (
                interpreter if interpreter.startswith("#!") else f"#!{interpreter}"
            )

        self._proxy: bytes | None = None
        self._host = host

        if interpreter is None:
            self._shebang = None
        else:
            self._shebang = (
                interpreter if interpreter.startswith("#!") else f"#!{interpreter}"
            )

        self._proxy = None

        if proxy_path:
            with open(proxy_path, "rb") as proxy_file:
                proxy = proxy_file.read()
                proxy = base64.encodebytes(proxy)
                self._proxy = proxy.replace(b"\n", b"")

        self._username = username
        self._ssh = self.establish_ssh_session(password, pkey_path)

    def establish_ssh_session(
        self, password: str | None, pkey_path: str | None
    ) -> paramiko.SSHClient:
        ssh = paramiko.SSHClient()
        ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))

        if pkey_path:
            pkey = paramiko.RSAKey(filename=pkey_path)
            ssh.connect(self._host, username=self._username, pkey=pkey)
        elif password:
            ssh.connect(self._host, username=self._username, password=password)
        else:
            raise ValueError(
                "Either 'password' or 'private_key_path' must be provided."
            )

        return ssh

    def _request(
        self, method: str, path: str, *, headers: dict[str, str] | None = None, **kwargs
    ) -> requests.Response:
        if self._proxy is None:
            raise AreqException("Proxy not initialized")

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

    def upload_file(self, local_file_path: str, remote_file_path: str) -> None:
        sftp = self._ssh.open_sftp()
        sftp.put(local_file_path, remote_file_path)
        sftp.close()

    def download_file(self, remote_file_path: str, local_file_path: str) -> None:
        sftp = self._ssh.open_sftp()
        sftp.get(remote_file_path, local_file_path)
        sftp.close()

    def create_and_download_proxy(
        self, proxy_passphrase: str, local_file_path: str
    ) -> None:
        _, _, stderr = self._ssh.exec_command(
            f"echo '{proxy_passphrase}' | grid-proxy-init -out ~/proxy -pwstdin",
            get_pty=True,
        )

        stderr_string = stderr.read().decode("ascii")

        if len(stderr_string) > 0:
            raise SSHException(f"Remote error: {stderr_string}")

        _, _, stderr = self._ssh.exec_command(
            "cat ~/proxy| base64 | tr -d '\\n' > proxy2", get_pty=True
        )

        stderr_string = stderr.read().decode("ascii")

        if len(stderr_string) > 0:
            raise SSHException(f"Remote error: {stderr_string}")

        self.download_file(
            f"/net/people/plgrid/{self._username}/proxy2", local_file_path
        )

        with open(local_file_path, "rb") as proxy_file:
            proxy = proxy_file.read()
            proxy = base64.encodebytes(proxy)
            proxy = proxy.replace(b"\n", b"")
            self._proxy = proxy
