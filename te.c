#include <stdio.h>

int helper(int x) {
  if (x <= 1) {
    return 1;
  } else if (x % 2 == 0) {
    return x + helper(x - 1);
  } else {
    return x + helper(x - 2);
  }
}

int classify(int x) {
  if (x < 0) {
    return -1;
  } else if (x == 0) {
    return 0;
  } else {
    return 1;
  }
}

int main(void) {
  int i = 0;
  int j = 0;
  int total = 0;

  while (i < 5) {
    if (i == 3) {
      i++;
      continue;
    }

    j = 0;
    while (j < 4) {
      if (j == 2 && i == 1) {
        j++;
        continue;
      } else if (j == 3 && i == 2) {
        break;
      } else if ((i + j) % 2 == 0) {
        total += helper(i + j);
        printf("even path: i=%d j=%d total=%d\n", i, j, total);
      } else {
        total += classify(i - j);
        printf("odd path: i=%d j=%d total=%d\n", i, j, total);
      }

      if (total > 30) {
        break;
      }

      j++;
    }

    if (total > 40) {
      break;
    } else if (total < 0) {
      total = 0;
    } else {
      total += i;
    }

    i++;
  }

  if (total > 20) {
    printf("large total: %d\n", total);
  } else if (total == 20) {
    printf("exact total: %d\n", total);
  } else {
    printf("small total: %d\n", total);
  }

  return 0;
}