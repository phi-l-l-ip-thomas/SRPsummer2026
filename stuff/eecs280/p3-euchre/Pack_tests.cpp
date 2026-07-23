#include "Pack.hpp"
#include "unit_test_framework.hpp"
#include <cassert>
#include <iostream>

using namespace std;

TEST(test_pack_default_ctor) {
    Pack pack;
    Card first = pack.deal_one();
    ASSERT_EQUAL(NINE, first.get_rank());
    ASSERT_EQUAL(SPADES, first.get_suit());
}

// Add more tests here
string make_test_pack() {
    return
    "Nine of Spades\n"
    "Ten of Spades\n"
    "Jack of Spades\n"
    "Queen of Spades\n"
    "King of Spades\n"
    "Ace of Spades\n"
    "Nine of Hearts\n"
    "Ten of Hearts\n"
    "Jack of Hearts\n"
    "Queen of Hearts\n"
    "King of Hearts\n"
    "Ace of Hearts\n"
    "Nine of Clubs\n"
    "Ten of Clubs\n"
    "Jack of Clubs\n"
    "Queen of Clubs\n"
    "King of Clubs\n"
    "Ace of Clubs\n"
    "Nine of Diamonds\n"
    "Ten of Diamonds\n"
    "Jack of Diamonds\n"
    "Queen of Diamonds\n"
    "King of Diamonds\n"
    "Ace of Diamonds\n";
}

void test_pack_deal_order() {
    istringstream iss(make_test_pack());
    Pack p(iss);

    for (int i = 0; i < 24; ++i) {
        Card c = p.deal_one();
        assert(c.get_rank() >= NINE);
    }
}

void test_pack_reset() {
    istringstream iss(make_test_pack());
    Pack p(iss);

    p.deal_one();
    p.deal_one();
    p.reset();

    Card c = p.deal_one();
    assert(c.get_rank() == NINE);
    assert(c.get_suit() == SPADES);
}

void test_pack_shuffle() {
    istringstream iss(make_test_pack());
    Pack p(iss);

    p.shuffle();
    for (int i = 0; i < 24; ++i) {
        p.deal_one();
    }
}

TEST_MAIN()
