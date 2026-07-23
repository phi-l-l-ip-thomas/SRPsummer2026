#include <iostream>
#include <fstream>
#include <vector>
#include "Player.hpp"
#include "Pack.hpp"
#include "Card.hpp"
using namespace std;

class Game {
public:
    Game(Pack pack_in, bool shuffle_in, int ptw_in, vector<Player*> p_in) :
        pack(pack_in), shuffle(shuffle_in), ptw(ptw_in),
        players(p_in), const_players(p_in) {}

    void play() {

        while (team1pts < ptw && team2pts < ptw) {

            dealer = (dealer + 1) % 4;

            cout << "Hand " << hand << endl;
            cout << players[dealer]->get_name()
                 << " deals" << endl;

            if (shuffle) pack.shuffle();
            else pack.reset();

            deal();

            Suit trump;
            make_trump(trump);

            play_hand(trump);

            ++hand;
            cout << endl;
        }

        if (team1pts > team2pts) {
            cout << players[0]->get_name() << " and "
                 << players[2]->get_name()
                 << " win!" << endl;
        } else {
            cout << players[1]->get_name() << " and "
                 << players[3]->get_name()
                 << " win!" << endl;
        }

        for (Player* p : players) {
            delete p;
        }
    }

private:
    Pack pack;
    bool shuffle;
    int ptw;
    int hand = 0;

    vector<Player*> players;
    const vector<Player*> const_players;

    int dealer = -1;
    int maker = -1;

    int team1pts = 0; 
    int team2pts = 0; 

    void deal() {

        const_players[(dealer + 1) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 1) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 1) % 4]->add_card(pack.deal_one());

        const_players[(dealer + 2) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 2) % 4]->add_card(pack.deal_one());

        const_players[(dealer + 3) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 3) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 3) % 4]->add_card(pack.deal_one());

        const_players[dealer]->add_card(pack.deal_one());
        const_players[dealer]->add_card(pack.deal_one());

        const_players[(dealer + 1) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 1) % 4]->add_card(pack.deal_one());

        const_players[(dealer + 2) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 2) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 2) % 4]->add_card(pack.deal_one());

        const_players[(dealer + 3) % 4]->add_card(pack.deal_one());
        const_players[(dealer + 3) % 4]->add_card(pack.deal_one());

        const_players[dealer]->add_card(pack.deal_one());
        const_players[dealer]->add_card(pack.deal_one());
        const_players[dealer]->add_card(pack.deal_one());
    }

    void trump_1(Card upcard, bool &ordered, Suit &order_up_suit) {
        for (int i = 1; i <= 4; ++i) {
            int idx = (dealer + i) % 4;
            bool is_dealer = (idx == dealer);

            if (const_players[idx]->make_trump(
                    upcard, is_dealer, 1, order_up_suit)) {

                cout << const_players[idx]->get_name()
                     << " orders up " << order_up_suit << endl;

                maker = idx;
                ordered = true;

                const_players[dealer]->add_and_discard(upcard);
                break;
            }
            else {
                cout << const_players[idx]->get_name()
                     << " passes" << endl;
            }
        }
    }

    void trump_2(Card upcard, bool &ordered, Suit &order_up_suit) {
        if (!ordered) {
            for (int i = 1; i <= 4; ++i) {
                int idx = (dealer + i) % 4;
                bool is_dealer = (idx == dealer);

                if (const_players[idx]->make_trump(
                        upcard, is_dealer, 2, order_up_suit)) {

                    cout << const_players[idx]->get_name()
                         << " orders up " << order_up_suit << endl;

                    maker = idx;
                    break;
                }
                else {
                    cout << const_players[idx]->get_name()
                         << " passes" << endl;
                }
            }
        }
    }
    void make_trump(Suit &order_up_suit) {

        Card upcard = pack.deal_one();
        cout << upcard << " turned up" << endl;

        bool ordered = false;
        trump_1(upcard, ordered, order_up_suit);
        trump_2(upcard, ordered, order_up_suit);

        cout << endl;
    }

    void play_hand(Suit trump) {

    int tricks02 = 0;
    int tricks13 = 0;

    int leader = (dealer + 1) % 4;

    for (int trick = 0; trick < 5; ++trick) {

        int second = (leader + 1) % 4;
        int third  = (leader + 2) % 4;
        int fourth = (leader + 3) % 4;

        Card c1 = players[leader]->lead_card(trump);
        cout << c1 << " led by "
             << players[leader]->get_name() << endl;

        Card c2 = players[second]->play_card(c1, trump);
        cout << c2 << " played by "
             << players[second]->get_name() << endl;

        Card c3 = players[third]->play_card(c1, trump);
        cout << c3 << " played by "
             << players[third]->get_name() << endl;

        Card c4 = players[fourth]->play_card(c1, trump);
        cout << c4 << " played by "
             << players[fourth]->get_name() << endl;

        Card winning = c1;
        int winner = leader;

        if (Card_less(winning, c2, c1, trump)) {
            winning = c2;
            winner = second;
        }
        if (Card_less(winning, c3, c1, trump)) {
            winning = c3;
            winner = third;
        }
        if (Card_less(winning, c4, c1, trump)) {
            winning = c4;
            winner = fourth;
        }

        cout << players[winner]->get_name()
             << " takes the trick" << endl;

        if (winner % 2 == 0) ++tricks02;
        else ++tricks13;

        leader = winner;

        cout << endl;
    }

    int maker_team = (maker % 2 == 0) ? 0 : 1;

    bool maker_wins =
        (maker_team == 0 && tricks02 >= 3) ||
        (maker_team == 1 && tricks13 >= 3);

    if (maker_wins) {

        int tricks = (maker_team == 0) ? tricks02 : tricks13;

        cout << players[maker_team]->get_name()
             << " and "
             << players[maker_team + 2]->get_name()
             << " win the hand" << endl;

        if (tricks == 5) {
            cout << "march!" << endl;
            if (maker_team == 0) team1pts += 2;
            else team2pts += 2;
        }
        else {
            if (maker_team == 0) team1pts += 1;
            else team2pts += 1;
        }
    }
    else {

        int defenders = 1 - maker_team;

        cout << players[defenders]->get_name()
             << " and "
             << players[defenders + 2]->get_name()
             << " win the hand" << endl;

        cout << "euchred!" << endl;

        if (defenders == 0) team1pts += 2;
        else team2pts += 2;
    }

    cout << players[0]->get_name()
         << " and " << players[2]->get_name()
         << " have " << team1pts << " points" << endl;

    cout << players[1]->get_name()
         << " and " << players[3]->get_name()
         << " have " << team2pts << " points" << endl;
    }
};

int main(int argc, char **argv) {

    if (argc != 12) {
        cout << "Usage: euchre.exe PACK_FILENAME [shuffle|noshuffle] "
             << "POINTS_TO_WIN NAME1 TYPE1 NAME2 TYPE2 "
             << "NAME3 TYPE3 NAME4 TYPE4" << endl;
        return 1;
    }

    string pack_filename = argv[1];
    ifstream fin(pack_filename);

    if (!fin.is_open()) {
        cout << "Error opening " << pack_filename << endl;
        return 2;
    }

    for (int i = 0; i < argc; ++i)
        cout << argv[i] << " ";
    cout << endl;

    Pack pack_in(fin);

    bool shuffle_in = (string(argv[2]) != "noshuffle");
    int ptw_in = stoi(argv[3]);

    vector<Player*> p_in;
    p_in.push_back(Player_factory(argv[4], argv[5]));
    p_in.push_back(Player_factory(argv[6], argv[7]));
    p_in.push_back(Player_factory(argv[8], argv[9]));
    p_in.push_back(Player_factory(argv[10], argv[11]));

    Game game(pack_in, shuffle_in, ptw_in, p_in);
    game.play();
}