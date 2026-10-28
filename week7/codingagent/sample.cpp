#include <iostream>

// Simple function to add two numbers
int add(int a, int b) {
    return a + b;
}

// Simple function to subtract two numbers
int subtract(int a, int b) {
    return a - b;
}

// Simple function to multiply two numbers
int multiply(int a, int b) {
    return a * b;
}

int main() {
    int x = 10;
    int y = 5;

    std::cout << "Add: " << add(x, y) << std::endl;
    std::cout << "Subtract: " << subtract(x, y) << std::endl;
    std::cout << "Multiply: " << multiply(x, y) << std::endl;

    return 0;
}
