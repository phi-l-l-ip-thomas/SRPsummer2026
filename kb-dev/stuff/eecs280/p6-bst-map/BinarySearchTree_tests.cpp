#include "BinarySearchTree.hpp"
#include "unit_test_framework.hpp"

TEST(test_stub) {
    ASSERT_TRUE(true);
}

// empty
TEST(is_empty) {
    BinarySearchTree<int> test;
    ASSERT_TRUE(test.empty());
}

TEST(not_empty) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(6);
    ASSERT_TRUE(!test.empty());
}
// height
TEST(height_is_empty) {
    BinarySearchTree<int> test;
    ASSERT_TRUE(test.height() == 0);
}

TEST(height_not_empty1) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(6);
    ASSERT_TRUE(test.height() == 2);
}

TEST(height_not_empty2) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    ASSERT_TRUE(test.height() == 4);
}
// size
TEST(size_is_empty) {
    BinarySearchTree<int> test;
    ASSERT_TRUE(test.size() == 0);
}

TEST(size_not_empty1) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(6);
    ASSERT_TRUE(test.size() == 2);
}

TEST(size_not_empty2) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    ASSERT_TRUE(test.size() == 6);
}
// find
TEST(find_is_empty) {
    BinarySearchTree<int> test;
    auto it = test.find(3);
    ASSERT_TRUE(it == test.end());
}

TEST(find_first) {
    BinarySearchTree<int> test;
    test.insert(2);
    test.insert(1);
    auto it = test.find(2);
    ASSERT_TRUE(*it == 2);
}

TEST(find_middle_right) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    auto it = test.find(19);
    ASSERT_TRUE(*it == 19);
}

TEST(find_end_left) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    auto it = test.find(2);
    ASSERT_TRUE(*it == 2);
}
// copy ctor
TEST(copy) {
    BinarySearchTree<int> test;
    test.insert(2);
    test.insert(1);
    test.insert(3);

    BinarySearchTree<int> check(test);
    ASSERT_TRUE(check.size() == 3);
    ASSERT_TRUE(check.height() == 2);
    auto it = check.find(2);
    ASSERT_TRUE(*it == 2);
    it = check.find(4);
    ASSERT_TRUE(it == check.end());
}
TEST(copy_empty) {
    BinarySearchTree<int> test;
    BinarySearchTree<int> check(test);
    ASSERT_TRUE(check.size() == 0);
    ASSERT_TRUE(check.height() == 0);
    auto it = check.find(2);
    ASSERT_TRUE(it == check.end());
}

TEST(copy_independence) {
    BinarySearchTree<int> a;
    a.insert(2);
    a.insert(1);
    a.insert(3);

    BinarySearchTree<int> b(a);

    *a.find(1) = 100;

    ASSERT_EQUAL(*b.find(1), 1);
}
TEST(copy_structure_preserved) {
    BinarySearchTree<int> a;

    a.insert(10);
    a.insert(5);
    a.insert(1);
    a.insert(7);
    a.insert(15);

    BinarySearchTree<int> b(a);

    ASSERT_EQUAL(a.size(), b.size());
    ASSERT_EQUAL(a.height(), b.height());

    auto it1 = a.begin();
    auto it2 = b.begin();

    while (it1 != a.end() && it2 != b.end()) {
        ASSERT_EQUAL(*it1, *it2);
        ++it1;
        ++it2;
    }

    ASSERT_TRUE(it1 == a.end());
    ASSERT_TRUE(it2 == b.end());
}
// assignment
TEST(assign) {
    BinarySearchTree<int> test;
    test.insert(2);
    test.insert(1);
    test.insert(3);

    BinarySearchTree<int> check = test;
    ASSERT_TRUE(check.size() == 3);
    ASSERT_TRUE(check.height() == 2);
    auto it = check.find(2);
    ASSERT_TRUE(*it == 2);
    it = check.find(4);
    ASSERT_TRUE(it == check.end());
}
TEST(assign_empty) {
    BinarySearchTree<int> test;
    BinarySearchTree<int> check = test;
    ASSERT_TRUE(check.size() == 0);
    ASSERT_TRUE(check.height() == 0);
    auto it = check.find(2);
    ASSERT_TRUE(it == check.end());
}
// min and max
TEST(minmax_empty) {
    BinarySearchTree<int> test;
    auto it = test.min_element();
    ASSERT_TRUE(it == test.end());
    it = test.max_element();
    ASSERT_TRUE(it == test.end());
}

TEST(minmax_not_empty1) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(6);
    ASSERT_TRUE(*test.min_element() == 4);
    ASSERT_TRUE(*test.max_element() == 6);
}

TEST(minmax_not_empty2) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    ASSERT_TRUE(*test.min_element() == 2);
    ASSERT_TRUE(*test.max_element() == 23);
}

TEST(minmax_not_empty3) {
    BinarySearchTree<int> test;
    test.insert(4);
    ASSERT_TRUE(*test.min_element() == 4);
    ASSERT_TRUE(*test.max_element() == 4);
}
// min greater than
TEST(ming_empty) {
    BinarySearchTree<int> test;
    auto it = test.min_greater_than(1);
    ASSERT_TRUE(it == test.end());
}

TEST(ming_not_empty1) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(6);
    ASSERT_TRUE(*test.min_greater_than(3) == 4);
    ASSERT_TRUE(*test.min_greater_than(4) == 6);
}

TEST(ming_not_empty2) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    ASSERT_TRUE(*test.min_greater_than(1) == 2);
    ASSERT_TRUE(*test.min_greater_than(17) == 19);
}

TEST(ming_not_empty3) {
    BinarySearchTree<int> test;
    test.insert(4);
    ASSERT_TRUE(*test.min_greater_than(0) == 4);
    auto it = test.min_greater_than(6);
    ASSERT_TRUE(it == test.end());
}

TEST(ming_above) {
    BinarySearchTree<int> test;
    test.insert(20);
    test.insert(10);
    test.insert(30);
    test.insert(25);

    ASSERT_EQUAL(*test.min_greater_than(25), 30);
}

TEST(ming_edge_cases) {
    BinarySearchTree<int> test;
    test.insert(2);
    test.insert(4);
    test.insert(6);

    ASSERT_TRUE(test.min_greater_than(6) == test.end());
    ASSERT_TRUE(test.min_greater_than(10) == test.end());
}
// check invariants
TEST(invar1) {
    BinarySearchTree<int> test;
    ASSERT_TRUE(test.check_sorting_invariant());
}

TEST(invar2) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    ASSERT_TRUE(test.check_sorting_invariant());
}

TEST(invar3) {
    BinarySearchTree<int> test;
    test.insert(4);
    test.insert(2);
    test.insert(20);
    test.insert(23);
    test.insert(19);
    test.insert(16);
    *test.begin() = 24;
    ASSERT_FALSE(test.check_sorting_invariant());
}

TEST(invar4) {
    BinarySearchTree<int> test;
    test.insert(10);
    test.insert(5);
    test.insert(15);
    test.insert(12);

    auto it = test.find(12);
    ASSERT_TRUE(it != test.end());
    *it = 3;
    ASSERT_FALSE(test.check_sorting_invariant());
}

TEST_MAIN()
