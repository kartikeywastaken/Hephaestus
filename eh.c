#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* helper_rec: recursive helper — should be classified as user, not a loop */
static int _helper_rec(int x) {
    if (x <= 0) return 0;
    if (x == 1) return 1;
    if (x % 2 == 0)
        return _helper_rec(x / 2) + _helper_rec(x / 2 - 1);
    return _helper_rec(x - 1) + _helper_rec(x - 2);
}

/* classify_pair: conditional chain — should reduce cleanly */
static const char *_classify_pair(int a, int b) {
    if (a > b)  return "greater";
    if (a < b)  return "less";
    if (a == 0) return "zero";
    if (a > 100) return "large";
    return "equal";
}

/* switchy: switch-like dispatch — should be preserved as switch_candidate */
static void _switchy(int x) {
    if (x == 1)      printf("one\n");
    else if (x == 2) printf("two\n");
    else if (x == 3) printf("three\n");
    else if (x == 4) printf("four\n");
    else             printf("other\n");
}

int main(int argc, char **argv) {
    int n = argc > 1 ? atoi(argv[1]) : 10;
    int r = _helper_rec(n);
    const char *cmp = _classify_pair(argc, n);
    _switchy(n % 5);
    printf("result=%d cmp=%s\n", r, cmp);
    return 0;
}
