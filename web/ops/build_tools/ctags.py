import subprocess as sp
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

_MAGIC = 'optimus'


class MainFoundException(Exception):
    pass


@dataclass
class Line:
    name: str
    path: str
    sign: str
    type: str


class Ctags:
    path: Path
    lines: list[Line]

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.lines = []
        with sp.Popen(f'ctags -R -f- {self.path}', stdout=sp.PIPE) as p:
            while line := p.stdout.readline():
                name, path, sign, typ = line.decode().strip().split('\t')
                if name == 'main' and typ == 'f':
                    raise MainFoundException
                self.lines.append(Line(name, path, sign.strip('/^$;"'), typ))

    @cached_property
    def signatures(self) -> list[Line]:
        return [l for l in self.lines if l.type == 'f']

    def resolve_signature(self) -> Line | None:
        if len(self.signatures) == 1:
            # print('found the only signature')
            return self.signatures[0]

        for l in self.signatures:
            if l.name == _MAGIC:
                # print('found magic signature')
                return l
        # print('found none')
        return None
