# Compiler
CXX ?= g++
CXXFLAGS ?= -Wall -Werror -pedantic -g --std=c++17 -Wno-sign-compare -Wno-comment
CXXFLAGS += -fsanitize=address

# Performance compiler flags
OPTFLAGS ?= --std=c++17 -Wall -Werror -pedantic -O3 -Wno-sign-compare -Wno-comment

# Add sanitizer flags for identifying undefined behavior.  The flags are
# different on macOS (AKA Darwin) and Windows/WSL/Linux.
UNAME := $(shell uname -s)
ifeq "$(UNAME)" "Darwin"
	CXXFLAGS += -fsanitize=address -fsanitize=undefined
else
	CXXFLAGS += -fsanitize=address -fsanitize=undefined -D_GLIBCXX_DEBUG
endif

test: CircularBuffer_tests.exe
	./CircularBuffer_tests.exe

CircularBuffer_tests.exe: CircularBuffer_tests.cpp CircularBuffer.hpp
	$(CXX) $(CXXFLAGS) $< -o $@

performance.exe: performance.cpp CircularBuffer.hpp
	$(CXX) $(OPTFLAGS) $< -o $@

.SUFFIXES:

.PHONY: clean

clean:
	rm -rvf *.out *.exe *.dSYM *.stackdump
