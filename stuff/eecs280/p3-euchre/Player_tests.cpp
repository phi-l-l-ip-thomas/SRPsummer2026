#include "Player.hpp"
#include "unit_test_framework.hpp"
#include <cassert>
#include <iostream>

using namespace std;

TEST(test_player_get_name) {
    Player * alice = Player_factory("Alice", "Simple");
    ASSERT_EQUAL("Alice", alice->get_name());

    delete alice;
}

// Add more tests here
TEST(test_add_card) {
    Player* p = Player_factory("A", "Simple");

    p->add_card(Card(NINE, CLUBS));
    p->add_card(Card(TEN, CLUBS));
    p->add_card(Card(JACK, CLUBS));
    p->add_card(Card(QUEEN, CLUBS));
    p->add_card(Card(KING, CLUBS));

    delete p;
}

TEST(test_make_trump_round1) {
    Player* p = Player_factory("A", "Simple");

    p->add_card(Card(ACE, HEARTS));
    p->add_card(Card(KING, HEARTS));
    p->add_card(Card(NINE, CLUBS));
    p->add_card(Card(NINE, SPADES));
    p->add_card(Card(NINE, DIAMONDS));

    Suit order;
    Card upcard(TEN, HEARTS);

    bool result = p->make_trump(upcard, false, 1, order);
    assert(result);
    assert(order == HEARTS);

    delete p;
}

TEST(test_make_trump_round2) {
    Player* p = Player_factory("A", "Simple");

    p->add_card(Card(ACE, DIAMONDS));
    p->add_card(Card(KING, DIAMONDS));
    p->add_card(Card(NINE, CLUBS));
    p->add_card(Card(NINE, SPADES));
    p->add_card(Card(NINE, HEARTS));

    Suit order;
    Card upcard(TEN, HEARTS);

    bool result = p->make_trump(upcard, false, 2, order);
    assert(result);
    assert(order == DIAMONDS);

    delete p;
}

TEST(test_lead_card_non_trump) {
    Player* p = Player_factory("A", "Simple");

    p->add_card(Card(ACE, CLUBS));
    p->add_card(Card(KING, HEARTS));
    p->add_card(Card(NINE, SPADES));
    p->add_card(Card(TEN, DIAMONDS));
    p->add_card(Card(QUEEN, HEARTS));

    Card led = p->lead_card(HEARTS);

    assert(led.get_rank() == ACE);
    assert(led.get_suit() == CLUBS);

    delete p;
}

TEST(test_play_card_follow_suit) {
    Player* p = Player_factory("A", "Simple");

    p->add_card(Card(ACE, CLUBS));
    p->add_card(Card(KING, CLUBS));
    p->add_card(Card(NINE, SPADES));
    p->add_card(Card(TEN, DIAMONDS));
    p->add_card(Card(QUEEN, HEARTS));

    Card led(KING, CLUBS);

    Card played = p->play_card(led, HEARTS);

    assert(played.get_suit() == CLUBS);

    delete p;
}

TEST_MAIN()
