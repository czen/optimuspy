from pathlib import Path

MAKEFILE = '''OFLAGS=-O3 -march=native
all: build test

build:
\tg++ $(OFLAGS) {} __optimus_tests.cpp ../../../catch2/catch_amalgamated.o -o __optimus_tests -I../../../catch2

test:
\t./__optimus_tests --benchmark-samples {} --out __optimus_tests.txt
'''

TESTS = '''#include "../../../catch2/catch_amalgamated.hpp"
#include "__optimus_debug_hook.h"

TEST_CASE("Optimus")
{
    BENCHMARK("opt_bench")
    {
        return %s();
    };
}
'''

DEBUG_HOOK = '''#pragma once
%s;
'''


def setup(path: Path, c_files: list[Path], f_name: str, f_sign: str, tests: int):
    with open(path / 'Makefile', 'w', encoding='utf8') as f:
        f.write(MAKEFILE.format(' '.join(f for f in c_files), tests))
    with open(path / '__optimus_debug_hook.h', 'w', encoding='utf8') as f:
        f.write(DEBUG_HOOK % f_sign)
    with open(path / '__optimus_tests.cpp', 'w', encoding='utf8') as f:
        f.write(TESTS % f_name)


def parse_benchmark(path: Path):
    v, u = -1, 'err'
    try:
        with open(path / '__optimus_tests.txt', 'r', encoding='utf8') as f:
            for line in f:
                if line.startswith('opt_bench'):
                    tokens = [i for i in f.readline().split(' ') if i]
                    return float(tokens[0]), tokens[1]
     # pylint: disable=broad-exception-caught
    except Exception as exc:
        print(exc)
    return v, u


def cleanup(path: Path, files: list[Path]):
    _files = set(file.name for file in files)
    for file in path.iterdir():
        if file.name not in _files:
            file.unlink()
