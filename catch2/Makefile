CFLAGS=-O3 -march=native

all: gpp

gpp:
	g++ $(CFLAGS) -c catch_amalgamated.cpp -o catch_amalgamated_g++.o

clang:
	clang++ $(CFLAGS) -c catch_amalgamated.cpp -o catch_amalgamated_clang++.o
