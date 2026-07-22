#include <vector>
#include <cassert>
#include "Cost.hpp"
using namespace std;

// REQUIRES: The prices and quantity vector are the same size.
// MODIFIES: Nothing
// EFFECTS: Calculates the total cost given the prices and quantity of prices.
double totalCost(vector<double> prices, vector<int> quantity) {
  // TODO: Assert that the price and quantity vectors are the same size.

  double total;
  for (size_t i = 0; i <= prices.size(); i++) {
    total += prices[i] * quantity[i];
  }
  return total;
}

