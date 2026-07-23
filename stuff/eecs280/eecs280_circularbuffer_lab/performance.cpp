// A program that compares a vector and CircularBuffer for implementing
// a queue. The program will run a series of push and pop operations on
// both the vector and CircularBuffer and compare the time it takes to
// run through a million operations.

#include <chrono>
#include <iostream>
#include <string>
#include <vector>
#include "CircularBuffer.hpp"

using namespace std;


static void test_vector(int N) {
  // Fill a vector with N integers
  vector<int> v;
  for (int i = 0; i < N; i++) {
    v.push_back(i);
  }

  // Push and pop N times
  for (int i = 0; i < N; i++) {
    v.push_back(i);
    // Vectors have no pop_front() function, but the
    // equivalent operation, v.erase(v.begin()) will remove
    // the first element and shift all the other elements down by one.
    v.erase(v.begin());
  }
}

// same as above but use a CircularBuffer instead of a vector
static void test_circularbuffer(int N) {
  CircularBuffer<int> rb;

  // Fill a CircularBuffer with N integers
  for (int i = 0; i < N; i++) {
    rb.push_back(i);
  }

  // Push and pop N times
  for (int i = 0; i < N; i++) {
    rb.push_back(i);
    rb.pop_front();
  }
}

// time vector and CircularBuffer operations, averaging over 5 runs
static void time_all(int N) {
  static const int NUM_ITERATIONS = 5;
  std::chrono::duration<double> vector_total =
    std::chrono::duration<double>::zero();
  std::chrono::duration<double> circularbuffer_total =
    std::chrono::duration<double>::zero();
  for (int i = 0; i < NUM_ITERATIONS; ++i) {
    std::chrono::time_point<std::chrono::system_clock> time1 =
      std::chrono::system_clock::now();
    test_vector(N);
    std::chrono::time_point<std::chrono::system_clock> time2 =
      std::chrono::system_clock::now();
    test_circularbuffer(N);
    std::chrono::time_point<std::chrono::system_clock> time3 =
      std::chrono::system_clock::now();
    vector_total += time2 - time1;
    circularbuffer_total += time3 - time2;
  }
  cout << "Average time for " << N << " elements with a vector: "
       << vector_total.count() / NUM_ITERATIONS << " seconds" << endl;
  cout << "Average time for " << N << " elements with a CircularBuffer: "
       << circularbuffer_total.count() / NUM_ITERATIONS << " seconds"
       << endl;
}


int main(int argc, char *argv[]) {
  if (argc != 2) {
    cout << "Usage: ./performance.exe [N]" << endl;
    return 1;
  }
  cout.precision(3);
  time_all(stoi(argv[1]));
}
