#include <stdio.h>

short gcd(short a, short b) {
    if (b > a) {
        short tmp = a;
        a = b;
        b = tmp;
    }

    while (a != 0 && b != 0) {
        short r = a % b;
        a = b;
        b = r;
    }

    if (a == 0)
        return b;
    else
        return a;
}

int main() {
    printf("gcd(4, 4) = %d\n", gcd(4, 4));
    printf("gcd(27, 36) = %d\n", gcd(27, 36));
    printf("gcd(270, 192) = %d\n", gcd(270, 192));

    return 0;
}
