#ifndef COST_HPP
#define COST_HPP

#include <vector>

// REQUIRES: The prices and quantity vector are the same size.
// MODIFIES: Nothing
// EFFECTS: Calculates the total cost given the prices and quantity of prices.
double totalCost(std::vector<double> prices, std::vector<int> quantity);

#endif // DATASET_HPP
