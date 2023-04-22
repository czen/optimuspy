from pathlib import Path

MAKEFILE = '''OFLAGS=-O3 -march=native
all: build test

build:
\tg++ $(OFLAGS) {} optimuspy_tests.cpp ../../catch2/catch_amalgamated.o -o optimuspy_tests -I../../catch2

test:
\t.\\optimuspy_tests.exe --benchmark-samples {} --benchmark-samples 1 --out optimuspy_tests.txt
'''

TESTS = '''#include "../../catch2/catch_amalgamated.hpp"
#include "optimuspy_debug_hook.h"

TEST_CASE("Main")
{
    BENCHMARK("main")
    {
        __optimuspy_main();
    };
}
'''

DEBUG_HOOK = '''#pragma once
int __optimuspy_main();
'''


def setup(path: Path, c_files: list[Path], tests: int):
    with open(path / 'Makefile', 'w', encoding='utf8') as f:
        f.write(MAKEFILE.format(' '.join(str(f.name) for f in c_files), tests))
    with open(path / 'optimuspy_debug_hook.h', 'w', encoding='utf8') as f:
        f.write(DEBUG_HOOK)
    with open(path / 'optimuspy_tests.cpp', 'w', encoding='utf8') as f:
        f.write(TESTS)


def patch_main(path: Path):
    for file in path.iterdir():
        if not file.is_file():
            continue
        found = False
        with open(file, 'r', encoding='utf8') as f:
            for line in f:
                if 'int main(' in line:
                    found = True
                    break
            if found:
                f.seek(0)
                with open(file.with_suffix('.tmp'), 'w', encoding='utf8') as w:
                    for line in f:
                        w.write(line.replace('main(', '__optimuspy_main('))
        if found:
            file.unlink()
            file.with_suffix('.tmp').rename(file)
