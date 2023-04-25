from pathlib import Path

MAKEFILE = '''OFLAGS=-O3 -march=native
all: build test

build:
\tg++ $(OFLAGS) {} __optimus_tests.cpp ../../../catch2/catch_amalgamated.o -o __optimuspy_tests -I../../../catch2

test:
\t./__optimus_tests.exe --benchmark-samples {} --out __optimus_tests.txt
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
%s
'''


def setup(path: Path, c_files: list[Path], f_name: str, f_sign: str, tests: int):
    with open(path / 'Makefile', 'w', encoding='utf8') as f:
        f.write(MAKEFILE.format(' '.join(f for f in c_files), tests))
    with open(path / '__optimus_debug_hook.h', 'w', encoding='utf8') as f:
        f.write(DEBUG_HOOK % f_sign)
    with open(path / '__optimus_tests.cpp', 'w', encoding='utf8') as f:
        f.write(TESTS % f_name)


def parse_benchmark(path: Path):
    with open(path / '__optimus_tests.txt', 'r', encoding='utf8') as f:
        while not f.readline().startswith('opt_bench'):
            pass
        try:
            tokens = [i for i in f.readline().split(' ') if i]
            v, u = float(tokens[0]), tokens[1]
        # pylint: disable=broad-exception-caught
        except Exception:
            return 0, 'err'
        return v, u
