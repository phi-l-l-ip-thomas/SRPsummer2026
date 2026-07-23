#include "Map.hpp"
#include "unit_test_framework.hpp"


TEST(test_empty_map) {
  Map<int, int> m;
  ASSERT_TRUE(m.empty());
  ASSERT_EQUAL(m.size(), 0);
  ASSERT_TRUE(m.begin() == m.end());
}

TEST(test_insert_basic) {
  Map<int, int> m;

  auto result = m.insert({5, 100});
  ASSERT_TRUE(result.second);
  ASSERT_EQUAL(result.first->first, 5);
  ASSERT_EQUAL(result.first->second, 100);

  ASSERT_FALSE(m.empty());
  ASSERT_EQUAL(m.size(), 1);
}

TEST(test_insert_duplicate) {
  Map<int, int> m;

  m.insert({5, 100});
  auto result = m.insert({5, 999});

  ASSERT_FALSE(result.second);
  ASSERT_EQUAL(result.first->second, 100);
  ASSERT_EQUAL(m.size(), 1);
}

TEST(test_bracket_insert_and_access) {
  Map<int, int> m;

  m[10] = 42;

  ASSERT_EQUAL(m.size(), 1);
  ASSERT_EQUAL(m[10], 42);
}

TEST(test_bracket_default_value) {
  Map<int, int> m;

  int val = m[7];
  ASSERT_EQUAL(val, 0);
  ASSERT_EQUAL(m.size(), 1);
}

TEST(test_find) {
  Map<int, int> m;

  m.insert({3, 30});
  m.insert({7, 70});

  auto it1 = m.find(3);
  ASSERT_TRUE(it1 != m.end());
  ASSERT_EQUAL(it1->second, 30);

  auto it2 = m.find(100);
  ASSERT_TRUE(it2 == m.end());
}

TEST(test_iteration_sorted_order) {
  Map<int, int> m;

  m.insert({5, 50});
  m.insert({2, 20});
  m.insert({8, 80});
  m.insert({1, 10});

  int expected_keys[] = {1, 2, 5, 8};
  int i = 0;

  for (auto it = m.begin(); it != m.end(); ++it) {
    ASSERT_EQUAL(it->first, expected_keys[i]);
    i++;
  }

  ASSERT_EQUAL(i, 4);
}

TEST(test_iterator_increment_to_end) {
  Map<int, int> m;

  m.insert({1, 10});
  m.insert({2, 20});

  auto it = m.begin();
  ++it;
  ++it;

  ASSERT_TRUE(it == m.end());
}

TEST(test_size_multiple_inserts) {
  Map<int, int> m;

  for (int i = 0; i < 10; i++) {
    m.insert({i, i * 10});
  }

  ASSERT_EQUAL(m.size(), 10);
}

TEST(test_bracket_overwrite) {
  Map<int, int> m;

  m[5] = 10;
  m[5] = 99;

  ASSERT_EQUAL(m.size(), 1);
  ASSERT_EQUAL(m[5], 99);
}

TEST(test_string_values) {
  Map<int, string> m;

  m[1] = "hello";
  m[2] = "world";

  ASSERT_EQUAL(m[1], "hello");
  ASSERT_EQUAL(m[2], "world");
}

TEST(test_unbalanced_increasing_insert) {
  Map<int, int> m;

  for (int i = 0; i < 20; i++) {
    m.insert({i, i});
  }

  ASSERT_EQUAL(m.size(), 20);

  int expected = 0;
  for (auto it = m.begin(); it != m.end(); ++it) {
    ASSERT_EQUAL(it->first, expected);
    expected++;
  }
}

TEST(test_reverse_insert) {
  Map<int, int> m;

  for (int i = 10; i >= 0; i--) {
    m.insert({i, i});
  }

  int expected = 0;
  for (auto it = m.begin(); it != m.end(); ++it) {
    ASSERT_EQUAL(it->first, expected);
    expected++;
  }
}

TEST_MAIN()
