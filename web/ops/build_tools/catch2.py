from pathlib import Path

MAKEFILE = '''OFLAGS=-O3 -march=native
all: build test

build:
\tg++ $(OFLAGS) {} __optimus_tests.cpp ../../catch2/catch_amalgamated.o -o __optimuspy_tests -I../../catch2

test:
\t.\\__optimus_tests.exe --benchmark-samples {} --benchmark-samples 1 --out __optimus_tests.txt
'''

TESTS = '''#include "../../catch2/catch_amalgamated.hpp"
#include "__optimus_debug_hook.h"

TEST_CASE("Optimus")
{
    BENCHMARK("opt")
    {
        return %s();
    };
}
'''

DEBUG_HOOK = '''#pragma once
%s
'''


def setup(path: Path, c_files: list[Path], tests: int):
    with open(path / 'Makefile', 'w', encoding='utf8') as f:
        f.write(MAKEFILE.format(' '.join(str(f.name) for f in c_files), tests))
    with open(path / '__optimus_debug_hook.h', 'w', encoding='utf8') as f:
        f.write(DEBUG_HOOK)
    with open(path / '__optimus_tests.cpp', 'w', encoding='utf8') as f:
        f.write(TESTS)
