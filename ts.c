#include <stdio.h>

typedef struct {
  int id;
  long score;
  char flag;
} Item;

long inspect(Item *p) {
  long total = 0;
  total += p->id;
  total += p->score;
  total += p->flag;
  return total;
}

int main(void) {
  Item item;
  item.id = 7;
  item.score = 100;
  item.flag = 3;
  printf("%ld\n", inspect(&item));
  return 0;
}