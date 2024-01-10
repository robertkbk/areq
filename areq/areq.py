import os
from collections.abc import Sequence
from typing import Literal, TypeAlias

import requests
import paramiko

from options import Options, to_sbatch_options
from response import Error, SubmitResponse
Hosts: TypeAlias = Literal["ares.cyfronet.pl"]


def _build_script(lines: Sequence[str], options: Options) -> str:
    if lines[0].startswith("#!"):
        return "\n".join([lines[0], *to_sbatch_options(options), *lines[1:]])

    return "\n".join([*to_sbatch_options(options), *lines])


class Areq:
    _BASE_URL = "https://submit.plgrid.pl/api/"

    def __init__(self, username: str, host: Hosts = "ares.cyfronet.pl", pkey_path: str = None, password: str = None) -> None:
        self._host = host
        self._username = username
        self._ssh = self.establish_ssh_session(password, pkey_path)
        
    def establish_ssh_session(
        self, 
        password: str, 
        pkey_path: str
    ) -> paramiko.SSHClient:
        ssh = paramiko.SSHClient()
        ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        if pkey_path:
            pkey = paramiko.RSAKey(filename=pkey_path)
            ssh.connect(self._host, username=self._username, pkey=pkey)
        elif password:
            ssh.connect(self._host, username=self._username, password=password)
        else:
            raise ValueError("Either 'password' or 'private_key_path' must be provided.")
        print("Established ssh session successfully.")
        return ssh
            
    def _request(self, method: str, path: str, *args, **kwargs) -> requests.Response:
        # TODO: Authentication
        return requests.request(method, self._BASE_URL + path, *args, **kwargs)

    def create(
        self,
        script: str,
        options: Options,
        working_directory: str | bytes | os.PathLike | None = None,
    ) -> SubmitResponse | Error:
        if len(lines := script.strip().splitlines()) == 0:
            raise ValueError("script is empty")

        body: dict[str, object] = {
            "host": self._host,
            "script": _build_script(lines, options),
        }

        if working_directory is not None:
            body["working_directory"] = working_directory

        response = self._request("POST", "jobs", json=body)
        return response.json()

    def status(
        self,
        job_ids: list[str],
        tag: str | None = None,
        format: str | None = None,
    ) -> list[SubmitResponse] | Error:
        response = self._request(
            "GET", "jobs", params={"job_id": job_ids, "tag": tag, "format": format}
        )
        return response.json()

    def upload_file(
        self,
        local_file_path: str,
        remote_file_path: str
    ) -> None:
        try:
            sftp = self._ssh.open_sftp()
            sftp.put(local_file_path, remote_file_path)
            sftp.close()
            print(f"Uploaded file successfully to path: {remote_file_path}")
        except Exception as e:
            print(f"Unable to upload the file. Error: {e}")
 