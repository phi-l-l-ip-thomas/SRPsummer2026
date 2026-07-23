#include "Player.hpp"
#include <algorithm>

using namespace std;

class SimplePlayer : public Player {
public:
  SimplePlayer(string name_in) : name(name_in) {}

  const string & get_name() const override {
    return name;
  }

  void add_card(const Card &c) override {
    hand.push_back(c);
  }

  bool make_trump(const Card &upcard, bool is_dealer,
                  int round, Suit &order_up_suit) const override {

    int count = 0;

    // ROUND 1
    if (round == 1) {
      for (const Card &card : hand) {
        if (card.is_trump(upcard.get_suit()) &&
            card.is_face_or_ace()) {
          ++count;
        }
      }
      if (count >= 2) {
        order_up_suit = upcard.get_suit();
        return true;
      }
      return false;
    }

    // ROUND 2
    Suit next = Suit_next(upcard.get_suit());

    if (!is_dealer) {
      for (const Card &card : hand) {
        if (card.is_trump(next) &&
            card.is_face_or_ace()) {
          ++count;
        }
      }
      if (count >= 1) {
        order_up_suit = next;
        return true;
      }
      return false;
    }

    order_up_suit = next;
    return true;
  }

  void add_and_discard(const Card &upcard) override {
    hand.push_back(upcard);

    int lowest_index = 0;

    for (int i = 1; i < hand.size(); ++i) {
        if (Card_less(hand[i], hand[lowest_index],
                      upcard.get_suit())) {
            lowest_index = i;
        }
    }

    hand.erase(hand.begin() + lowest_index);
}

  Card lead_card(Suit trump) override {

    int best_index = -1;

    for (int i = 0; i < hand.size(); ++i) {
        if (!hand[i].is_trump(trump)) {
            if (best_index == -1 ||
                hand[best_index] < hand[i]) {
                best_index = i;
            }
        }
    }

    if (best_index == -1) {
        best_index = 0;
        for (int i = 1; i < hand.size(); ++i) {
            if (Card_less(hand[best_index],
                          hand[i],
                          trump)) {
                best_index = i;
            }
        }
    }

    Card chosen = hand[best_index];
    hand.erase(hand.begin() + best_index);
    return chosen;
}

  virtual Card play_card(const Card &led_card, Suit trump) override {

    int follow_index = -1;

    for (int i = 0; i < hand.size(); ++i) {
        if (hand[i].get_suit(trump) ==
            led_card.get_suit(trump)) {

            if (follow_index == -1 ||
                Card_less(hand[follow_index],
                          hand[i],
                          led_card,
                          trump)) {
                follow_index = i;
            }
        }
    }

    if (follow_index != -1) {
        Card chosen = hand[follow_index];
        hand.erase(hand.begin() + follow_index);
        return chosen;
    }

    int lowest_index = 0;
    for (int i = 1; i < hand.size(); ++i) {
        if (Card_less(hand[i],
                      hand[lowest_index],
                      led_card,
                      trump)) {
            lowest_index = i;
        }
    }

    Card chosen = hand[lowest_index];
    hand.erase(hand.begin() + lowest_index);
    return chosen;
}

private:
  string name;
  vector<Card> hand;
};

class HumanPlayer : public Player {
public:
  HumanPlayer(string name_in) : name(name_in) {}

  const string & get_name() const override {
    return name;
  }

  void add_card(const Card &c) override {
    hand.push_back(c);
    sort(hand.begin(), hand.end());
  }

  bool make_trump(const Card &upcard, bool is_dealer,
                  int round, Suit &order_up_suit) const override {

    print_hand();
    cout << "Human player " << name
         << ", please enter a suit, or \"pass\":\n";

    string decision;
    cin >> decision;

    if (decision != "pass") {
      order_up_suit = string_to_suit(decision);
      return true;
    }

    return false;
  }

  void add_and_discard(const Card &upcard) override {
    hand.push_back(upcard);
    sort(hand.begin(), hand.end());

    print_hand();
    cout << "Discard upcard: [-1]\n";
    cout << "Human player " << name
         << ", please select a card to discard:\n";

    int choice;
    cin >> choice;

    if (choice != -1) {
      hand.erase(hand.begin() + choice);
    } else {
      hand.erase(hand.end() - 1);
    }
  }

  Card lead_card(Suit trump) override {
    print_hand();
    cout << "Human player " << name
         << ", please select a card:\n";

    int choice;
    cin >> choice;

    Card chosen = hand[choice];
    hand.erase(hand.begin() + choice);
    return chosen;
  }

  Card play_card(const Card &led_card, Suit trump) override {
    print_hand();
    cout << "Human player " << name
         << ", please select a card:\n";

    int choice;
    cin >> choice;

    Card chosen = hand[choice];
    hand.erase(hand.begin() + choice);
    return chosen;
  }

private:
  string name;
  vector<Card> hand;

  void print_hand() const {
    for (size_t i = 0; i < hand.size(); ++i) {
      cout << "Human player " << name
           << "'s hand: "
           << "[" << i << "] "
           << hand[i] << "\n";
    }
  }
};

Player * Player_factory(const string &name,
                         const string &strategy) {

  if (strategy == "Simple") {
    return new SimplePlayer(name);
  }
  else if (strategy == "Human") {
    return new HumanPlayer(name);
  }

  return nullptr;
}

ostream & operator<<(ostream &os, const Player &p) {
  os << p.get_name();
  return os;
}