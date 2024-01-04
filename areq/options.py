from datetime import timedelta
from typing import Annotated, Literal, ParamSpec, TypeAlias, TypedDict
from typing import get_origin, get_type_hints

PartitionType: TypeAlias = Literal[
    "plgrid",
    "plgrid-testing",
    "plgrid-now",
    "plgrid-long",
    "plgrid-bigmem",
    "plgrid-gpu-v100",
]


class Options(TypedDict, total=False):
    partition: PartitionType
    time: Annotated[str | timedelta, "time"]
    nodes: int
    ntasks: int
    error: str
    account: str
    output: str
    memory: Annotated[str | int, "mem"]
    gpus: int
    input: str
    job_name: Annotated[str, "job-name"]
    cpus_per_task: Annotated[str, "cpus-per-task"]


def _get_name(hint: ParamSpec, option: str) -> str:
    return hint.__metadata__[0] if get_origin(hint) is Annotated else option  # type: ignore


def to_sbatch_options(options: Options) -> list[str]:
    hints = get_type_hints(Options, include_extras=True)

    return [
        f'#SBATCH --{_get_name(hints[name], name)}="{option}"'
        for name, option in options.items()
    ]
