#ifndef CIRCULARBUFFER_HPP
#define CIRCULARBUFFER_HPP

#include <iostream>
#include <cassert>

template <typename T>
class CircularBuffer {

public:

  // EFFECTS: Constructs an empty CircularBuffer.
  CircularBuffer()
    : data(new T[INITIAL_CAPACITY]),
    head(0), tail(0), num_elts(0), capacity(INITIAL_CAPACITY) {

  }

  // Copy constructor -- we'll cover this SOON(TM).
  CircularBuffer(const CircularBuffer<T> &other)
    : data(new T[other.capacity]),
      capacity(other.capacity) {
    copy_data_from(other);
  }
  ~CircularBuffer() {
    delete[] data;
  }
  // MODIFIES: *this
  // EFFECTS:  Adds a new value to the back of the buffer
  //           moves tail to the new position
  void push_back(const T &value) {
    if (num_elts == capacity) {
      grow();
    }
    data[tail] = value;
    tail = (tail + 1) % capacity;
    ++num_elts;
  }

  // REQUIRES: buffer is not empty
  // MODIFIES: *this
  // EFFECTS:  Removes the element at the front of the buffer
  //           moves head to the new position
  void pop_front() {
    head = (head + 1) % capacity;
    --num_elts;
  }

  // REQUIRES: buffer is not empty
  // EFFECTS:  Returns the value at the front of the buffer
  T &front() {
    return data[head];
  }

  // EFFECTS:  Returns the current size of the buffer
  int size() const {
    return num_elts;
  }

  // EFFECTS:  Returns true if this CircularBuffer is empty, false otherwise.
  bool empty() const {
    return num_elts == 0;
  }

  // REQUIRES: 0 <= index and index < number of elements in this CircularBuffer.
  // EFFECTS:  Returns (by reference) the element that is index positions from head.
  T & at(int index) {
    return data[(head + index) % capacity];
  }

  // REQUIRES: 0 <= index and index < number of elements in this CircularBuffer.
  // EFFECTS:  Returns (by const reference) the element that is index positions from head.
  const T & at(int index) const {
    return data[(head + index) % capacity];
  }

  // EFFECTS:  Prints the buffer to os.
  void print(std::ostream &os) const{
    os << "[ ";
    for (int i = 0; i < num_elts; ++i) {
        os << at(i);
        if (i < num_elts - 1) {
            os << ", ";
        }
    }
    os << " ]";
  }

private:

  // The initial capacity of a CircularBuffer when it is created
  static const int INITIAL_CAPACITY = 4;

  // The array to hold the N elements stored in this circular buffer in positions determined
  // by head and tail
  T * data;      // INVARIANT: data points to the start of an array of capacity elements

  // head is the index marking the beginning of the data in the buffer
  // tail is the index where a new element would be added in the buffer
  // num_elts is the number of elements currently in the buffer
  int head;      // INVARIANT: 0 <= head < capacity
  int tail;      // INVARIANT: 0 <= tail < capacity
  int num_elts;  // INVARIANT: 0 <= num_elts <= capacity
  int capacity;

  // MODIFIES: *this
  // EFFECTS:  Replaces the array used to store the elements with a
  //           new, larger array.
  void grow() {
    T* temp = new T[capacity * 2];

    for (int i = 0; i < num_elts; ++i) {
      temp[i] = this->at(i);   
    }

    delete[] data;             
    data = temp;              
    head = 0;                 
    tail = num_elts;
    capacity *= 2;
  }

  // REQUIRES: this CircularBuffer has capacity >= other.num_elts
  // MODIFIES: *this
  // EFFECTS:  Copies all elements from the other circular buffer into this one,
  //           replacing any existing elements. They are copied to beginning
  //           of the data array and the head/tail are adjusted accordingly.
  void copy_data_from(const CircularBuffer &other) {

    // Copy elements from other, placing at the start of our own array
    for(int i = 0; i < other.num_elts; ++i) {
      // using .at(i) accounts for possibly different head/tail of other
      data[i] = other.at(i);
    }

    // Adjust head/tail and num_elts to match new data
    head = 0;
    tail = other.num_elts;
    num_elts = other.num_elts;
  }

};

// EFFECTS:  overloaded operator that prints the buffer to os
template <typename T>
std::ostream& operator<<(std::ostream &os, const CircularBuffer<T> &rb) {
  rb.print(os);
  return os;
}

#endif // Do not remove this. Write all your code above this line.
