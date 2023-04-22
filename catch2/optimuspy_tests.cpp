#include "catch_amalgamated.hpp"
#include <unistd.h>

TEST_CASE("Main")
{
    BENCHMARK("main")
    {
        execl("./a.exe", NULL);
    };
}
