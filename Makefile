.DEFAULT_GOAL := all
CXX = g++
CXXFLAGS = -O2 -Wall -Wextra -Wpedantic -std=c++17
CPPFLAGS = -I.
include algorithm.mk
# The branch's policy is compiled in; no environment variable is needed to grade it.
POLICY_CPPFLAGS = $(if $(strip $(GRADING_POLICY)),-DSCHEDULER_FIXED_POLICY=\"$(GRADING_POLICY)\",)

# These simulator objects are supplied without their sources. Never delete them.
SIM_OBJECTS = Init.o Machine.o main.o Simulator.o Task.o VM.o
TARGET = simulator

.PHONY: all clean test benchmark report FORCE
FORCE:
all: $(TARGET)
scheduler: Scheduler.o $(SIM_OBJECTS)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o $@ $^
$(TARGET): Scheduler.o $(SIM_OBJECTS)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o $@ $^
Scheduler.o: Scheduler.cpp Scheduler.hpp Interfaces.h SimTypes.h algorithm.mk Makefile FORCE
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $(POLICY_CPPFLAGS) -c $< -o $@
clean:
	rm -f Scheduler.o $(TARGET) scheduler tests/scheduler_test
test: $(TARGET)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -DSCHEDULER_ENGINE_TEST -o tests/scheduler_test tests/scheduler_test.cpp
	./tests/scheduler_test
	python3 tests/tooling.py
	python3 tests/integration.py $(if $(strip $(GRADING_POLICY)),--policy $(GRADING_POLICY),)
benchmark: $(TARGET)
	python3 tools/benchmark.py $(if $(strip $(GRADING_POLICY)),--policies $(GRADING_POLICY) --output results/$(GRADING_POLICY)_benchmark.csv,)

report:
	python3 tools/summarize.py
	pdflatex -interaction=nonstopmode -halt-on-error report_updated.tex
