#include "tutorial.hpp"
#include "unit_test_framework.hpp"

// We define a test case with the TEST(<test_name>) macro.
// <test_name> can be any valid C++ function name.
#include <vector>
#include "tutorial.hpp"
#include "unit_test_framework.hpp"

using namespace std;

TEST(test_slide_right_1) {
    vector<int> v = { 4, 0, 1, 3, 3 };
    vector<int> expected = { 3, 4, 0, 1, 3 };
    slideRight(v);
    ASSERT_SEQUENCE_EQUAL(v, expected);
}

TEST(test_slide_right_1entry) {
    vector<int> v = {4};
    vector<int> expected = {4};
     slideRight(v);
     ASSERT_SEQUENCE_EQUAL(v, expected);
}

TEST(test_slide_right_0entry) {
    vector<int> v = {};
    vector<int> expected = {};
    slideRight(v);
    ASSERT_SEQUENCE_EQUAL(v, expected);
}

TEST(test_slide_right_2) {
    vector<int> v = {4, 4, 3, 2};
    vector<int> expected = {2, 4, 4, 3};
    slideRight(v);
    ASSERT_SEQUENCE_EQUAL(v, expected);
}

TEST(test_slide_right_3) {
    vector<int> v = {4, -4, -3, 2};
    vector<int> expected = {2, 4, -4, -3};
    slideRight(v);
    ASSERT_SEQUENCE_EQUAL(v, expected);
}

TEST(test_flip_1) {
   std::vector<int> v1 = {1, 2, 3, 4, 5};
   std::vector<int> expected1 = {5, 4, 3, 2, 1};
   flip(v1);
   ASSERT_SEQUENCE_EQUAL(v1, expected1);
}

TEST(test_flip_2) {
   std::vector<int> v2 = {3, 5, 7, 9, 8};
   std::vector<int> expected2 = {8, 9, 7, 5, 3};
   flip(v2);
   ASSERT_SEQUENCE_EQUAL(v2, expected2);
}


TEST(test_flip_3) {
   std::vector<int> v3 = {-1, -2, -3, 0, -5};
   std::vector<int> expected3 = {-5, 0, -3, -2, -1};
   flip(v3);
   ASSERT_SEQUENCE_EQUAL(v3, expected3);
}

TEST(test_flip_4) {
   std::vector<int> v4 = {};
   std::vector<int> expected4 = {};
   flip(v4);
   ASSERT_SEQUENCE_EQUAL(v4, expected4);
}

TEST(test_flip_5) {
   std::vector<int> v5 = {1,1,1,1,1};
   std::vector<int> expected5 = {1,1,1,1,1};
   flip(v5);
   ASSERT_SEQUENCE_EQUAL(v5, expected5);
}

TEST(test_flip_6) {
    std::vector<int> v6 = {1,2,3,4};
   std::vector<int> expected6 = {4,3,2,1};
   flip(v6);
   ASSERT_SEQUENCE_EQUAL(v6, expected6);
}

TEST_MAIN() // No semicolon!
