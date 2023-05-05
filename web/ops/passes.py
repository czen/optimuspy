import subprocess as sp
from enum import Enum
from pathlib import Path

from django.conf import settings


class Pass():
    '''Проход без аргументов. Не делает оптимизаций.'''
    args: list[str] = []
    _c_files: list[Path]

    def __init__(self, c_files: list[Path]) -> None:
        self._c_files = c_files

    def run(self) -> int:
        code = 0
        for file in self._c_files:
            with sp.Popen([f'{settings.OPSC_PATH}/opsc', *self.args, f'{file}', '-o', f'{file}']) as p:
                code = max(code, p.wait())
        return code


class OMPPass(Pass):
    '''Проход с бэкендом OpenMP'''
    args = ['-backend=openmp']


class Passes(Enum):
    NoOptPass = 0
    OMPPass = 1

    @property
    def obj(self) -> Pass | None:
        match self:
            case Passes.NoOptPass:
                return Pass
            case Passes.OMPPass:
                return OMPPass
        return None

    def __str__(self) -> str:
        return self.name

    @property
    def desc(self) -> str:
        match self:
            case Passes.NoOptPass:
                return 'Без оптимизации'
            case Passes.OMPPass:
                return 'OpenMP backend'
        return super().__str__()
