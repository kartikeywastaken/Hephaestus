#include <stdint.h>
#include <stdio.h>

typedef int (*op_fn)(int, int);

static int op_add(int a, int b) { return a + b; }

static int op_xor(int a, int b) { return a ^ b; }

static int mix_value(int x) {
  int acc = x;

  for (int i = 0; i < 6; i++) {
    acc = (acc * 17) + i;

    if ((acc & 3) == 1) {
      acc ^= 0x55;
    } else {
      acc += 7;
    }
  }

  return acc;
}

static int reduce_weird(int *arr, int n, op_fn fn) {
  int acc = 0;

  for (int i = 0; i < n; i++) {
    int v = arr[i];

    if ((v & 1) == 0) {
      acc = fn(acc, v);
    } else {
      acc = acc + mix_value(v);
    }

    if ((acc & 15) == 9) {
      break;
    }

    if ((acc & 7) == 3) {
      continue;
    }

    acc ^= i;
  }

  return acc;
}

static int nested_control(int seed) {
  int out = seed;

  for (int outer = 0; outer < 4; outer++) {
    for (int inner = 0; inner < 5; inner++) {
      int t = outer * 10 + inner;

      if ((t & 1) == 0) {
        out += t;
      } else {
        out ^= t;
      }
    }

    if ((out & 31) == 17) {
      out += 100;
    } else {
      out -= 3;
    }
  }

  return out;
}

int main(void) {
  int values[10];

  for (int i = 0; i < 10; i++) {
    values[i] = i * 5 + 1;
  }

  int a = reduce_weird(values, 10, op_add);
  int b = reduce_weird(values, 10, op_xor);
  int c = nested_control(a ^ b);

  printf("a=%d b=%d c=%d\n", a, b, c);

  return c & 63;
}