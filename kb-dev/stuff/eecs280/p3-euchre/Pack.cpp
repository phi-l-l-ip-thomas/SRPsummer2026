#include "Pack.hpp"
#include<vector>
using namespace std;
  // EFFECTS: Initializes the Pack to be in the following standard order:
  //          the cards of the lowest suit arranged from lowest rank to
  //          highest rank, followed by the cards of the next lowest suit
  //          in order from lowest to highest rank, and so on. 
  // NOTE: The standard order is the same as that in pack.in.
  // NOTE: Do NOT use pack.in in your implementation of this function
  // NOTE: The pack is initially full, with no cards dealt.
  
  constexpr const char *const RANK_NAMES[] = {
  "Two",   // TWO
  "Three", // THREE
  "Four",  // FOUR
  "Five",  // FIVE
  "Six",   // SIX
  "Seven", // SEVEN
  "Eight", // EIGHT
  "Nine",  // NINE
  "Ten",   // TEN
  "Jack",  // JACK
  "Queen", // QUEEN
  "King",  // KING
  "Ace"    // ACE
};

constexpr const char *const SUIT_NAMES[] = {
  "Spades",   // SPADES
  "Hearts",   // HEARTS
  "Clubs",    // CLUBS
  "Diamonds", // DIAMONDS
};

  Pack::Pack() {
    next = 0;
    int index = 0;
      for (string suit : SUIT_NAMES) {
        for (int rank = 7; rank < 13; ++rank) {
          cards[index] = Card(string_to_rank(RANK_NAMES[rank]), string_to_suit(suit));
          ++index;
        }
      }
  }

  // REQUIRES: pack_input contains a representation of a Pack in the
  //           format required by the project specification
  // MODIFIES: pack_input
  // EFFECTS: Initializes Pack by reading from pack_input.
  // NOTE: The pack is initially full, with no cards dealt.
  Pack::Pack(std::istream& pack_input) {
    next = 0;
    for (int i = 0; i < 24; ++i) {
      Card card_in;
      pack_input >> card_in;
      cards[i] = card_in;
    }
  }

  // REQUIRES: cards remain in the Pack
  // EFFECTS: Returns the next card in the pack and increments the next index
  Card Pack::deal_one() {
    return cards[next++];
  }

  // EFFECTS: Resets next index to first card in the Pack
  void Pack::reset() {
    next = 0;
  }

  // EFFECTS: Shuffles the Pack and resets the next index. This
  //          performs an in shuffle seven times. See
  //          https://en.wikipedia.org/wiki/In_shuffle.
  void Pack::shuffle() {
    for (int count = 0; count < 7; ++count) {
      vector<Card> temp;
      for (int i = 0; i < 12; ++i) {
        Card low_card = cards[i];
        Card high_card = cards[i+12];
        temp.push_back(high_card);
        temp.push_back(low_card);
      }

      for (int i = 0; i < PACK_SIZE; ++i) {
        cards[i] = temp[i];
      }
    }
    reset();
  }

  // EFFECTS: returns true if there are no more cards left in the pack
  bool Pack::empty() const {
    return next == PACK_SIZE;
  }