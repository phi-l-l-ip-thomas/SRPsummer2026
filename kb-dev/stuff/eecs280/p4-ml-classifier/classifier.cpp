#include<cmath>
#include<set>
#include<map>
#include<sstream>
#include "csvstream.hpp"
using namespace std;

// EFFECTS: Return a set of unique whitespace delimited words
set<string> unique_words(const string &str) {
    istringstream source(str);
    set<string> words;
    string word;
    while (source >> word) {
        words.insert(word);
    }
    return words;
}

// Helper insertion overloads for map testing
ostream &operator<<(ostream &lhs, map<string, int> &data) {
    for (const auto& pair : data) {
        cout << "Key: " << pair.first << ", Value: " << pair.second << std::endl;
    }
    return lhs;
}

ostream &operator<<(ostream &lhs, map<string, set<string>> &data) {
    for (auto& pair : data) {
        cout << "labels" << endl;
        cout << "Key: " << pair.first << ", Value: ";
        for (const auto& entry : pair.second) {
            cout << entry << " ";
        }
        cout << endl;
    }
    return lhs;
}

ostream &operator<<(ostream &lhs, const map<string, map<string, int>> &data) {
    for (auto& val : data) {
        cout << "labels" << endl;
        cout << "Label: " << val.first << endl;
        for (const auto& entry : val.second) {
            cout << "word: " << entry.first << ", count: " << entry.second << endl;
        }
        cout << endl;
    }
    return lhs;
}

class Classifier {
public:
    void train(csvstream &csvin, map<string, string> &row) {
        while (csvin >> row) {
            ++post_count;
            auto insertion = vocab.insert({row["tag"], unique_words(row["content"])});
            vocab[row["tag"]] = unique_words(row["content"]);
            
            //Updates label counts
            if (training) {
                cout << "  label = " << row["tag"];
                cout << ", content = " << row["content"] << endl;
            }
            if (insertion.second == true) {
                label_counts[row["tag"]] = 1;
            }
            if (insertion.second == false) {
                ++label_counts[row["tag"]];
            }
            
            //Updates word counts
            for (string word : vocab[row["tag"]]) {
                auto insertion = word_counts.insert({word, 0});
                if (insertion.second == true) {
                    word_counts[word] = 1;
                }
                else if (insertion.second == false) {
                    ++word_counts[word];
                }

                // Updates LWC
                auto lwc_insertion = label_word_counts[row["tag"]].insert({word, 0});
                if (lwc_insertion.second == true) {
                    label_word_counts[row["tag"]][word] = 1; 
                }
                else if (lwc_insertion.second == false) {
                    ++label_word_counts[row["tag"]][word];
                }
            }
        }
    }

    Classifier(csvstream &csvin) {
        training = true;
        // Iterate through and read in CSV
        map<string, string> row;
        cout << "training data:" << endl;
        train(csvin, row);
        
        cout << "trained on " << post_count << " examples" << endl;
        
        cout << "vocabulary size = " << word_counts.size() << endl << endl;

        cout << "classes:" << endl;
        for (auto entry : label_counts) {
            cout << "  " << entry.first << ", " << entry.second 
                << " examples, log-prior = "
                << log_prior(entry.first) << endl;
        }

        cout << "classifier parameters:" << endl;
        for (auto label : label_word_counts) {
            for (auto entry : label.second) {
                cout << "  " << label.first << ":" << entry.first 
                << ", count = " << entry.second
                    << ", log-likelihood = " 
                    << log_likelihood(entry.first, label.first) << endl;
            }
        }
        cout << endl;
    }

    Classifier(csvstream &csvin, csvstream &csvtest) {
        training = false;
        // Iterate through and read in CSV
        map<string, string> row;
        train(csvin, row);
        
        cout << "trained on " << post_count << " examples" << endl << endl;

        cout << "test data:" << endl;
        
        while (csvtest >> row) {
            set<string> words = unique_words(row["content"]);
            string prediction = row["tag"];
            float log_prob_score = log_prob(words, row["tag"]);
            
            for (auto label : label_counts) {
                if (log_prob(words, label.first) > log_prob_score) {
                    prediction = label.first;
                    log_prob_score = log_prob(words, label.first);
                }
            }
            if (prediction == row["tag"]) {++correct;}
            ++total;

            cout << "  correct = " << row["tag"] 
            << ", predicted = " << prediction
                << ", log-probability score = " 
                << log_prob_score << endl;
            cout << "  content = " << row["content"] << endl << endl;
        }
        cout << "performance: " << correct << " / " << total 
        << " posts predicted correctly" << endl;
    }
    
    //Prediction
    float log_prior(string C) {
        return log((double)label_counts[C] / post_count);
    }

    float log_likelihood(string w, string C) {
        if (word_counts.find(w) == word_counts.end()) {
            return log(1.0 / post_count);
        }
        if (label_word_counts[C].find(w) == label_word_counts[C].end()) {
            return log((double)word_counts[w] / post_count);
        }

        return log((double)label_word_counts[C][w] / label_counts[C]);
    }

    float log_prob(set<string> strings, string C) {
        float sum = log_prior(C);
        for (string w : strings) {
            sum += log_likelihood(w, C);
        }
        return sum;
    }

    // Output functions
    void print() {
        cout << "vocab: " << endl << vocab << endl;
        cout << "word_counts: " << endl << word_counts << endl;
        cout << "label_counts: " << endl << label_counts << endl;
        cout << "lwcounts" << endl << label_word_counts << endl;
        cout << "post count: " << post_count << endl;
    }

private:
    map<string, set<string>> vocab;
    map<string, map<string, int>> label_word_counts;
    map<string, int> word_counts;
    map<string, int> label_counts;
    int post_count = 0;
    int tag_i;
    int content_i;
    bool training;
    int correct = 0;
    int total = 0;
};

int main(int argc, char *argv[]) {
    cout.precision(3);
    if (argc == 2) {
        string csv_file = argv[1];
        try {
            csvstream csvin(csv_file, ',', false);
            Classifier test(csvin);
            
        } catch(const csvstream_exception &e) {
            cout << "Error opening file: " << csv_file << endl;
            return 1;
        }
    } else if (argc == 3) {
        string csv_file = argv[1];
        string test_file = argv[2];
        try {
            csvstream csvin(csv_file, ',', false);
            csvstream csvtestin(test_file, ',', false);
            Classifier test(csvin, csvtestin);
            
        } catch(const csvstream_exception &e) {
            cout << "Error opening file: " << csv_file << endl;
            return 1;
        }
    } else {
        cout << "Usage: classifier.exe TRAIN_FILE [TEST_FILE]" << endl;
        return 1;
    }
}