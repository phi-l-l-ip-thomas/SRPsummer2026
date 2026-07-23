#include <iostream>
#include <string>
#include "Cost.hpp"
using namespace std;

int main() {
    vector<string> Menu_Items = {"Yummy Steak", "Mac n Cheese", "Lobster", "Salad", "Refillable Drink"};
    vector<double> Prices = {49.99, 19.99, 100.00, 9.99, 4.67};
    vector<int> Quantities_Ordered = {12, 63, 65, 66, 92};

    // Print Summary of items ordered
    cout << "Today at the Lobster280, we had the following orders" << endl;
    for (size_t i = 0; i < Menu_Items.size(); i++) {
        cout << "  - " << Menu_Items[i]
             << " ($" << Prices[i] << "): "
             << Quantities_Ordered[i] << " ordered\n";
    }

    cout << "We made a profit of $" << totalCost(Prices, Quantities_Ordered) << endl;
}
