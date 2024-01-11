import os
from collections.abc import Sequence
from time import sleep
from typing import Literal, TypeAlias, Dict
from tensorflow.keras.models import Sequential


import requests
import paramiko

from .options import Options, to_sbatch_options
from .tensorflow_model_handler import TensorflowModelHandler
from .response import Error, SubmitResponse
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
        self._proxy_path = None
        
    def establish_ssh_session(
        self, 
        password: str, 
        pkey_path: str
    ) -> paramiko.SSHClient | Error:
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
        sftp = self._ssh.open_sftp()
        sftp.put(local_file_path, remote_file_path)
        sftp.close()
        print(f"Uploaded file successfully to path: {remote_file_path}")
            
    def download_file(
        self,
        remote_file_path: str,
        local_file_path: str
    ) -> None:
        sftp = self._ssh.open_sftp()
        sftp.get(remote_file_path, local_file_path)
        sftp.close()
        print(f"Downloaded file successfully to path: {remote_file_path}")
 
    def create_and_download_proxy(
        self,
        proxy_passphrase: str,
        local_file_path: str
    ) -> None:
        _, stdout, stderr = self._ssh.exec_command(f'echo {proxy_passphrase} | grid-proxy-init -out ~/proxy -pwstdin', get_pty=True)
        
        stderr_string = stderr.read().decode('ascii')
        stdout_string = stdout.read().decode('ascii')
        print(stdout_string, stderr_string)
        if len(stderr_string) > 0:
            raise Error(f'Got remote error : {stderr_string}')
        
        _, stdout, stderr = self._ssh.exec_command('cat ~/proxy| base64 | tr -d \'\\n\' > proxy2', get_pty=True)
        
        stderr_string = stderr.read().decode('ascii')
        stdout_string = stdout.read().decode('ascii')
        print(stdout_string, stderr_string)
        if len(stderr_string) > 0:
            raise Error(f'Got remote error : {stderr_string}')
        
        self.download_file(f'/net/people/plgrid/{self._username}/proxy2', local_file_path)
        self._proxy_path = local_file_path
    
    def fit_model(
        self,
        model: any,
        x_train: any,
        y_train: any,
        training_config: any
    ) -> (any, Dict[str, any]):
        if isinstance(model, Sequential):
            tf_model_handler = TensorflowModelHandler()
            model_path = tf_model_handler.save_model(model)
            x_train_path, y_train_path = tf_model_handler.save_dataset(x_train, y_train)
            training_config_path = tf_model_handler.save_training_config(training_config)
            
            self.upload_file(model_path,f'/net/people/plgrid/{self._username}/areq/model.keras')
            self.upload_file(x_train_path,f'/net/people/plgrid/{self._username}/areq/x_train.npy')
            self.upload_file(y_train_path,f'/net/people/plgrid/{self._username}/areq/y_train.npy')
            self.upload_file(training_config_path,f'/net/people/plgrid/{self._username}/areq/training_config.json')
            
            # TODO: change path in case of using in package
            self.upload_file('./areq/resources/tensorflow_default_script.py',f'/net/people/plgrid/{self._username}/areq/default_script.py')
            
            # TODO: submit the job
            print('Waiting to be started')
            sleep(1)
            
            print('Waiting to be finished')
            sleep(1)
            # TODO: wait for the results
            
            self.download_file(f'/net/people/plgrid/{self._username}/areq/weights.h5','./weights.h5')
            self.download_file(f'/net/people/plgrid/{self._username}/areq/history.json','./history.json')
            sleep(1)
            return tf_model_handler.load_trained_model('./weights.h5','./history.json')
            

        