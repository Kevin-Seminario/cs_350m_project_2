CXX = g++
CXXFLAGS = -O2 -Wall -Wextra -Wpedantic -std=c++17
CPPFLAGS = -I.

# These simulator objects are supplied without their sources. Never delete them.
SIM_OBJECTS = Init.o Machine.o main.o Simulator.o Task.o VM.o
TARGET = simulator

.PHONY: all clean test benchmark report
all: $(TARGET)
scheduler: Scheduler.o $(SIM_OBJECTS)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o $@ $^
$(TARGET): Scheduler.o $(SIM_OBJECTS)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o $@ $^
Scheduler.o: Scheduler.cpp Scheduler.hpp Interfaces.h SimTypes.h
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@
clean:
	rm -f Scheduler.o $(TARGET) scheduler tests/scheduler_test
test: $(TARGET)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o tests/scheduler_test tests/scheduler_test.cpp
	./tests/scheduler_test
	python3 tests/integration.py
benchmark: $(TARGET)
	python3 tools/benchmark.py

report:
	python3 tools/summarize.py
	pdflatex -interaction=nonstopmode -halt-on-error report.tex
