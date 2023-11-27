import subprocess as sp
from enum import Enum
from pathlib import Path

from django.conf import settings


class Pass:
    '''Проход без аргументов. Не делает оптимизаций.'''
    args: list[str] = ['-backend=plain', '-flattice', '-fmontego']
    _c_files: list[Path]

    def __init__(self, c_files: list[Path]) -> None:
        self._c_files = c_files

    def run(self) -> int:
        code = 0
        for file in self._c_files:
            with sp.Popen([f'{settings.OPSC_PATH}/opsc', *self.args, *settings.INCLUDES, '-o', f'{file}', f'{file}']) as p:
                code = max(code, p.wait())
        return code


class OMPPass(Pass):
    '''Проход с бэкендом OpenMP'''
    args = ['-backend=openmp', '-flattice', '-fmontego']


class TilingPass(Pass):
    '''Проход с Tiling бэкендом'''
    #args = ['-backend=tiling', '-flattice', '-fmontego', '-rtails']
    args = ['-backend=wavefront']


class Passes(Enum):
    NoOptPass = 0
    OMPPass = 1
    TilingPass = 2

    @property
    def obj(self) -> Pass | None:
        match self:
            case Passes.NoOptPass:
                return Pass
            case Passes.OMPPass:
                return OMPPass
            case Passes.TilingPass:
                return TilingPass
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
            case Passes.TilingPass:
                return 'Tiling backend'
        return super().__str__()

    @property
    def short(self):
        match self:
            case Passes.NoOptPass:
                return 'NoOpt'
            case Passes.OMPPass:
                return 'OMP'
            case Passes.TilingPass:
                return 'Tiling'
        return super().__str__()
