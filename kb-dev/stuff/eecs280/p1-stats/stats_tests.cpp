/* stats_tests.cpp
 *
 * Unit tests for the simple statistics library
 *
 * EECS 280 Statistics Project
 *
 * Protip #1: Write tests for the functions BEFORE you implement them!  For
 * example, write tests for median() first, and then write median().  It sounds
 * like a pain, but it helps make sure that you are never under the illusion
 * that your code works when it's actually full of bugs.
 *
 * Protip #2: Instead of putting all your tests in main(),  put each test case
 * in a function!
 */


#include "stats.hpp"
#include <iostream>
#include <cassert>
#include <vector>
#include <cmath>
using namespace std;

void count_one();
void count_reverse();
void count_repeat();
void sum_negative();
void sum_zeros();
void sum_repeat();
void sum_one();
void mean_one(); 
void mean_negative();
void mean_even();
void mean_odd();
void min_one();
void max_one(); 
void std_dev_two();
void std_dev_repeat();
void std_dev_negative();
void percentile_one_none();
void percentile_one_all();
void percentile_negative(); 
void filter_all();
void filter_none();
void filter_small();

// Precision for floating point comparison
const double epsilon = 0.00001;

static bool almost_equal(double x, double y) {
  return abs(x - y) < epsilon;
}

// Add prototypes for you test functions here.


int main() {
  
  count_one();
  count_reverse();
  count_repeat();
  sum_negative();
  sum_zeros();
  sum_repeat();
  sum_one();
  mean_one(); 
  mean_negative();
  mean_even();
  mean_odd();
  min_one();
  max_one(); 
  std_dev_two();
  std_dev_repeat();
  std_dev_negative();
  percentile_one_none();
  percentile_one_all();
  percentile_negative(); 
  filter_all();
  filter_none();
  filter_small();

  return 0;
}

void count_one() {
  assert(count({4}) == 1);
}

void count_reverse() {
  assert(count({5, -1, 4}) == 3);
}

void count_repeat() {
  assert(count({3, 3, 2}) == 3);
}

void sum_negative() {
  assert(sum({-1, 2, -4, 0}) == -3);
}

void sum_zeros() {
  assert(sum({0, 0, 0, 0}) == 0);
}

void sum_repeat() {
  assert(sum({2, 2, 0, 1}) == 5);
}

void sum_one() {
  assert(sum({4}) == 4);
}

void mean_one() {
  assert(almost_equal(mean({4}), 4));
}

void mean_negative() {
  assert(almost_equal(mean({-2, 2}), 0));
}

void mean_even() {
  assert(almost_equal(mean({2,3}), 2.5));
}

void mean_odd() {
  assert(almost_equal(mean({2,3,4}), 3));
}

void min_one() {
  assert(min({4}) == 4);
}

void max_one() {
  assert(max({4}) == 4);
}

void std_dev_two() {
  assert(almost_equal(stdev({3,4}), .707107));
}

void std_dev_repeat() {
  assert(almost_equal(stdev({3,3}), 0));
}

void std_dev_negative() {
  assert(almost_equal(stdev({-3,4}), 4.9497474683058));
}

void percentile_one_none() {
  assert(percentile({1}, 0) == 1);
}

void percentile_one_all() {
  assert(percentile({1}, 1) == 1);
}

void percentile_negative() {
  assert(percentile({-2, 4, -10, 30}, .5) < 4);
  assert(percentile({-2, 4, -10, 30}, .5) > -2);
}

void filter_all() {
  assert(filter({3,4,5}, {1, 1, 1}, 1) == vector<double>({3, 4, 5}));
}

void filter_none() {
  assert(filter({3,4,5}, {0,0,0}, 1).empty());
}

void filter_small(){
  assert(filter({-3,4,5}, {1, 0, 1}, 1) == vector<double>({-3, 5}));
}