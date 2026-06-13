#include <stdio.h>

int helper_rec(int x) {
  if (x <= 0) {
    return 0;
  } else if (x == 1) {
    return 1;
  } else if (x % 3 == 0) {
    return x + helper_rec(x - 1);
  } else if (x % 2 == 0) {
    return x + helper_rec(x - 2);
  } else {
    return x + helper_rec(x - 3);
  }
}

int classify_pair(int a, int b) {
  if (a < 0 && b < 0) {
    return -3;
  } else if (a < 0) {
    return -2;
  } else if (b < 0) {
    return -1;
  } else if (a == b) {
    return 0;
  } else if (a > b) {
    return 1;
  } else {
    return 2;
  }
}

int switchy(int x) {
  switch (x % 5) {
  case 0:
    return 10;
  case 1:
    return 20;
  case 2:
    return 30;
  case 3:
    return 40;
  default:
    return 50;
  }
}

int main(void) {
  int i = 0, j = 0, k = 0;
  int total = 0;
  int guard = 0;

  while (i < 6) {
    if (i == 1) {
      i++;
      continue;
    }

    j = 0;
    while (j < 5) {
      if (j == 2 && i == 4) {
        break;
      }

      if (j == 1) {
        j++;
        continue;
      }

      k = 0;
      while (k < 4) {
        if (k == 2 && j == 3) {
          break;
        }

        if ((i + j + k) % 2 == 0) {
          total += helper_rec(i + j + k);
        } else if ((i + j + k) % 3 == 0) {
          total += classify_pair(i - j, j - k);
        } else {
          total += switchy(i + j + k);
        }

        if (total > 120) {
          break;
        } else if (total < -20) {
          total = 0;
          k++;
          continue;
        } else if (total % 7 == 0) {
          guard++;
        } else {
          guard += 2;
        }

        k++;
      }

      if (total > 150) {
        break;
      } else if (guard > 20) {
        j++;
        continue;
      } else {
        total += j;
      }

      j++;
    }

    if (total > 200) {
      break;
    } else if (total < 10) {
      total += 5;
    } else if (total % 3 == 0) {
      total -= i;
    } else {
      total += i;
    }

    i++;
  }

  if (total > 180) {
    printf("huge total: %d %d\n", total, guard);
  } else if (total > 100) {
    printf("medium total: %d %d\n", total, guard);
  } else if (total == 42) {
    printf("special total: %d %d\n", total, guard);
  } else {
    printf("small total: %d %d\n", total, guard);
  }

  return 0;
}