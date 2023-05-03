from abc import ABC, abstractmethod
from enum import Enum


def singleton(cls):
    _instances = {}

    def getinstance(*args, **kwargs):
        if cls not in _instances:
            _instances[cls] = cls(*args, **kwargs)
        return _instances[cls]
    return getinstance


class Compiler(ABC):
    class olevels(Enum):
        L0: str = '-O0 -march=native'
        L1: str = '-O1 -march=native'
        L2: str = '-O2 -march=native'
        L3: str = '-O2 -march=native'
    out: str = '-o'

    @property
    @abstractmethod
    def name(self):
        ...

    def __iter__(self):
        for l in self.olevels:
            yield l.value


@singleton
class GCC(Compiler):
    @property
    def name(self):
        return 'g++'


@singleton
class Clang(Compiler):
    @property
    def name(self):
        return 'clang++'


@singleton
class MSVC(Compiler):
    class olevels(Enum):
        L0: str = '/O0 /arch:AVX2'
        L1: str = '/O1 /arch:AVX2'
        L2: str = '/O2 /arch:AVX2'
    out: str = '/Fe:'

    @property
    def name(self):
        return 'cl'


class Compilers(Enum):
    GCC = 0
    Clang = 1
    # MSVC = 2

    @property
    def obj(self) -> Compiler | None:
        match self:
            case Compilers.GCC:
                return GCC()
            case Compilers.Clang:
                return Clang()
            # case Compilers.MSVC:
            #     return MSVC()
        return None
