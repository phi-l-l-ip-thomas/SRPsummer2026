#include "Card.hpp"
#include "unit_test_framework.hpp"
#include <iostream>
#include <cassert>
using namespace std;


TEST(test_card_ctor) {
    Card c(ACE, HEARTS);
    ASSERT_EQUAL(ACE, c.get_rank());
    ASSERT_EQUAL(HEARTS, c.get_suit());
}

// Add more test cases here
TEST(test_is_face_or_ace) {
    assert(!Card(NINE, CLUBS).is_face_or_ace());
    assert(!Card(TEN, HEARTS).is_face_or_ace());
    assert(Card(JACK, CLUBS).is_face_or_ace());
    assert(Card(QUEEN, SPADES).is_face_or_ace());
    assert(Card(KING, HEARTS).is_face_or_ace());
    assert(Card(ACE, DIAMONDS).is_face_or_ace());
}

TEST(test_effective_suit_left_bower) {
    Card right(JACK, HEARTS);
    Card left(JACK, DIAMONDS);

    assert(right.get_suit(HEARTS) == HEARTS);
    assert(left.get_suit(HEARTS) == HEARTS);

    Card left_other(JACK, CLUBS);
    assert(left_other.get_suit(SPADES) == SPADES);
}

TEST(test_same_suit_ordering) {
    Card nine(NINE, CLUBS);
    Card ten(TEN, CLUBS);
    Card ace(ACE, CLUBS);

    Card led = nine;

    assert(Card_less(nine, ten, led, HEARTS));
    assert(Card_less(ten, ace, led, HEARTS));
    assert(!Card_less(ace, nine, led, HEARTS));
}

TEST(test_trump_beats_non_trump) {
    Card trump_card(NINE, HEARTS);
    Card non_trump(ACE, CLUBS);

    Card led = non_trump;

    assert(Card_less(non_trump, trump_card, led, HEARTS));
    assert(!Card_less(trump_card, non_trump, led, HEARTS));
}

TEST(test_right_bower_highest) {
    Card right(JACK, HEARTS);
    Card ace_trump(ACE, HEARTS);

    Card led = ace_trump;

    assert(Card_less(ace_trump, right, led, HEARTS));
}

TEST(test_left_bower_second_highest) {
    Card right(JACK, HEARTS);
    Card left(JACK, DIAMONDS);
    Card ace_trump(ACE, HEARTS);

    Card led = ace_trump;

    assert(Card_less(ace_trump, left, led, HEARTS));
    assert(Card_less(left, right, led, HEARTS));
}

TEST(test_led_suit_following) {
    Card led(KING, CLUBS);
    Card queen_clubs(QUEEN, CLUBS);
    Card off_suit(NINE, DIAMONDS);

    assert(Card_less(queen_clubs, led, led, HEARTS));
    assert(Card_less(off_suit, queen_clubs, led, HEARTS));
}

TEST(test_trump_over_led) {
    Card led(KING, CLUBS);
    Card trump(NINE, HEARTS);

    assert(Card_less(led, trump, led, HEARTS));
}

TEST(test_left_bower_counts_as_trump) {
    Card led(KING, CLUBS);
    Card left(JACK, DIAMONDS);

    assert(Card_less(led, left, led, HEARTS));
}

TEST_MAIN()
