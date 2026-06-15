#include <stdint.h>
#include <stdio.h>

typedef int (*OpFn)(int, int);

static int op_add(int a, int b) { return a + b; }

static int op_xor(int a, int b) { return a ^ b; }

static int reduce_array(int *arr, int n, OpFn fn) {
  int acc = 0;

  for (int i = 0; i < n; i++) {
    int v = arr[i];

    if ((v & 1) == 0) {
      acc = fn(acc, v);
    } else {
      acc = acc + (v * 3);
    }
  }

  return acc;
}

static int weird_loop(int seed) {
  int acc = seed;

  for (int i = 0; i < 32; i++) {
    acc = (acc * 1103515245 + 12345) >> 3;

    if ((acc & 7) == 3) {
      continue;
    }

    if ((acc & 15) == 9) {
      break;
    }

    acc ^= i;
  }

  return acc;
}

int main(void) {
  int values[8];

  for (int i = 0; i < 8; i++) {
    values[i] = i * 7 + 1;
  }

  int a = reduce_array(values, 8, op_add);
  int b = reduce_array(values, 8, op_xor);
  int c = weird_loop(a ^ b);

  printf("a=%d b=%d c=%d\n", a, b, c);

  return c & 31;
}