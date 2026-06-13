#include <stdio.h>

int main(void) {
  int i = 0, j = 0, total = 0;

  while (i < 5) {
    j = 0;
    while (j < 5) {
      if (j == 1) {
        j++;
        continue;
      }

      if (i == 3 && j == 2) {
        break;
      }

      total += i + j;
      j++;
    }

    if (total > 20) {
      break;
    } else if (total < 5) {
      total += 10;
    } else {
      total += 1;
    }

    i++;
  }

  if (total > 15) {
    printf("large %d\n", total);
  } else {
    printf("small %d\n", total);
  }

  return 0;
}