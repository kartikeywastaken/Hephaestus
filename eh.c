#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
  int value = 0;
  if (argc > 1) {
    value = atoi(argv[1]);
  }
  printf("%d\n", value);
  return 0;
}
