// stats.cpp
#include "stats.hpp"
#include <cassert>
#include <vector>
#include <algorithm> // sort
#include <cmath> // sqrt, modf

using namespace std;

int count(std::vector<double> v) {
  return v.size();
}

double sum(vector<double> v) {
  double total = 0;
  for (double entry : v) {
    total += entry;
  }
  return total;
}

double mean(vector<double> v) {
  return sum(v) / static_cast<double>(count(v));
}

double median(vector<double> v) {
  sort(v.begin(), v.end());
  if (count(v) % 2 == 0) {
    return (v[static_cast<double>(count(v)) / 2 - 1.5] + v[count(v) - .5]) / 2;
  } else {
    return v[static_cast<double>(count(v)) / 2 - .5];
  }
}

double min(vector<double> v) {
  double val = v[0];
  for (double entry : v) {
    if (entry < val) { val = entry;}
  }
  return val;
}

double max(vector<double> v) {
  double val = v[0];
  for (double entry : v) {
    if (entry > val) { val = entry;}
  }
  return val;
}

double stdev(vector<double> v) {
  double summation = 0;
  double v_mean = mean(v);
  for (double entry : v) {
    summation += pow(entry - v_mean, 2);
  }
  return sqrt(summation / (count(v) - 1));
}

double percentile(vector<double> v, double p) {
  double rank = p * (count(v) - 1) + 1;
  double k = 0;
  double d = modf(rank, &k);

  sort(v.begin(), v.end());

  if (d == 0) { 
    return v[k-1];
  } else {
    return v[k-1] + d * (v[k] - v[k-1]);
  }
  
}

vector<double> filter(vector<double> v,
                      vector<double> criteria,
                      double target) {
  vector<double> filtered;
  for (int i = 0; i < count(v); i++) {
    if (criteria[i] == target) {
      filtered.push_back(v[i]);
    }
  }
  return filtered;
}