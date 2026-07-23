#include<vector>
#include<iostream>
#include<fstream>
#include<set>
#include<map>
using namespace std;

//Structs
struct Person {
    int age;
    string name;
    bool isNinja;
}; //SEMICOLON

// Classes
class Bird {
public:
    Bird(const string &name_in, const int age_in) :
        age(age_in), name(name_in) {}
    Bird(const string &name_in) :
        Bird(name_in, 0) {}
    string get_name() {
        return name;
    }
    virtual void speak() {
        cout << "tweet";
    }
private:
    string name;
    int age;
};

class Chicken : public Bird { // Constructing chicken calls bird constructor FIRST
public:
    Chicken(const string &name_in) :
        Bird(name_in), roads_crossed(0) {}
    virtual void speak() override {
        cout << "quackkck";
    }
private:
    int roads_crossed;
};

// Set containers
class Queue {
    void insert();
    void remove();
private:
    set<string> unique_words(const string &filename);
};

// Templates
template<class T>
class UnsortedSet {
public:
    void insert(T v);
private:
    T elts[ELTS_CAP];
    static const int ELTS_CAP;
};

template<class T>
T max(T val1, T val2) {}
template<class T>
void UnsortedSet<T>::insert(T v) {}

// Operator overloading
ostream &operator<<(ostream &os, const Chicken &c) {
    cout << "add stuff duh";
    return os;
}

int main() {
    int x = 3;
    int y = 5;
    
    // References
    int &r = x;

    // Pointers
    int *wow = &x;
    cout << wow; // 0x1000
    cout << *wow; // 3
    cout << &wow; // 0x1008
    *wow = 8; // now x = 8
    wow = &y; // wow points to y
    int **wow2 = &wow;
    cout << **wow2; // 5

    const int *p1 = &x; // x cannot be modified through p1 >> *p1 = 0 doesn't work
    int const *p01 = &x; // same as above
    int * const p1 = &x; // p1 forever points to &x

    // Arrays and vectors
    int arr[3] = {1, 2, 3};
    cout << arr; // &arr[0]
    cout << *arr; // 1
    cout << arr + 2; // &arr[2]

    // Iterators
    vector<int> v = {3, 4, 5};
    vector<int>::iterator iter = v.begin();
    iter += 3; // "Random-access indexing"
    for (vector<int>::iterator it = v.begin(); it != v.end(); ++it) {}

    // Structs
    Person alex = {25, "alex", false};
    alex.isNinja = true; //changes member var

    // Maps
    map<string, int> scores;
    scores["Ben"] = 100;

    //Streams (for CLI, int arg[c] and char** argv[])
    string s;
    cin >> s;
    // File Streams #include<fstream>
    ifstream fin("order.txt"); // creates pointer to buffer
    if (!fin.is_open()) {return 1;}
    string item;
    fin >> item;
    string word;
    while (fin >> word) {}
    string line;
    getline(fin, line);
    fin.close();

    string a = "10";
    cout << stoi(a); // prints INTEGER... stod for doubles
}

// Unit Testing Framework
TEST(test_effective_suit_left_bower) {
    Card right(JACK, HEARTS);
    Card left(JACK, DIAMONDS);

    assert(right.get_suit(HEARTS) == HEARTS);
    assert(left.get_suit(HEARTS) == HEARTS);

    Card left_other(JACK, CLUBS);
    assert(left_other.get_suit(SPADES) == SPADES);
}
