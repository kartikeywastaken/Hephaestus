
#include <stdint.h>
#include <stdio.h>

#define MAX_ITEMS 6
#define NAME_LEN 8

typedef struct {
  int x;
  int y;
} Point;

typedef struct {
  int id;
  long score;
  char flag;
  int values[4];
  Point pos;
} Item;

typedef struct {
  Item items[MAX_ITEMS];
  int count;
  long checksum;
  char tag;
} Container;

typedef int (*ScoreFn)(Item *it, int bias);

int basic_score(Item *it, int bias) {
  int total = 0;

  total += it->id;
  total += (int)(it->score % 97);
  total += it->flag;
  total += it->pos.x;
  total -= it->pos.y;

  for (int i = 0; i < 4; i++) {
    total += it->values[i];
  }

  return total + bias;
}

int weird_score(Item *it, int bias) {
  int total = bias;

  for (int i = 3; i >= 0; i--) {
    if (it->values[i] == 0) {
      continue;
    }

    if (it->values[i] < 0) {
      total -= it->values[i];
    } else {
      total += it->values[i] * (i + 1);
    }
  }

  if (it->flag & 1) {
    total += it->id * 2;
  } else {
    total -= it->id;
  }

  total += (int)(it->score & 0xff);
  return total;
}

int recursive_mix(int n) {
  if (n <= 0) {
    return 1;
  }

  if (n == 1) {
    return 2;
  }

  if (n % 2 == 0) {
    return n + recursive_mix(n - 2);
  }

  return n + recursive_mix(n - 1);
}

void init_item(Item *it, int seed) {
  it->id = seed;
  it->score = seed * 100L + 13;
  it->flag = (char)(seed % 5);
  it->pos.x = seed * 2;
  it->pos.y = seed - 3;

  for (int i = 0; i < 4; i++) {
    it->values[i] = seed + i;
  }

  if (seed % 3 == 0) {
    it->values[2] = -seed;
  }

  if (seed == 4) {
    it->flag = 7;
  }
}

void init_container(Container *c) {
  c->count = MAX_ITEMS;
  c->checksum = 0;
  c->tag = 'A';

  for (int i = 0; i < MAX_ITEMS; i++) {
    init_item(&c->items[i], i + 1);
  }
}

long update_checksum(Container *c) {
  long acc = 0;

  for (int i = 0; i < c->count; i++) {
    Item *it = &c->items[i];

    acc += it->id;
    acc += it->score;
    acc += it->flag;
    acc += it->pos.x;
    acc += it->pos.y;

    for (int j = 0; j < 4; j++) {
      acc += it->values[j];
    }
  }

  c->checksum = acc;
  return acc;
}

int classify_item(Item *it) {
  int bucket = 0;

  switch (it->flag) {
  case 0:
    bucket = it->id + 10;
    break;
  case 1:
    bucket = it->values[0] + 20;
    break;
  case 2:
    bucket = it->values[1] + 30;
    break;
  case 3:
    bucket = it->pos.x + 40;
    break;
  case 4:
    bucket = it->pos.y + 50;
    break;
  default:
    bucket = (int)(it->score % 100);
    break;
  }

  return bucket;
}

int process_item(Item *it, ScoreFn fn, int bias) {
  int score = fn(it, bias);
  int class_id = classify_item(it);

  if (score > 200) {
    score -= recursive_mix(it->id);
  } else if (score < 50) {
    score += recursive_mix(it->flag);
  } else {
    score += class_id;
  }

  return score;
}

int scan_container(Container *c, int limit) {
  int result = 0;

  for (int i = 0; i < c->count; i++) {
    Item *it = &c->items[i];

    if (it->id == 2) {
      continue;
    }

    if (it->id > limit) {
      break;
    }

    ScoreFn fn;

    if (it->flag & 1) {
      fn = weird_score;
    } else {
      fn = basic_score;
    }

    result += process_item(it, fn, i * 3);

    if (result > 500) {
      result -= classify_item(it);
    }
  }

  return result;
}

void mutate_alias(Item *a, Item *b) {
  a->values[0] += 1;
  b->values[1] += 2;

  if (a == b) {
    a->score += 5;
    return;
  }

  if (a->id < b->id) {
    a->pos.x += b->pos.y;
    b->pos.y -= a->flag;
  } else {
    b->pos.x += a->pos.y;
    a->pos.y -= b->flag;
  }
}

long pointer_walk(Container *c) {
  long total = 0;
  Item *begin = &c->items[0];
  Item *end = &c->items[c->count];

  for (Item *p = begin; p < end; p++) {
    total += p->id;
    total += p->score;

    if (p->flag == 7) {
      total += p->values[3];
    }
  }

  return total;
}

int nested_branches(Container *c) {
  int out = 0;

  for (int i = 0; i < c->count; i++) {
    Item *it = &c->items[i];

    if (it->flag == 0) {
      out += it->id;
    } else if (it->flag == 1) {
      if (it->values[0] > 2) {
        out += it->values[0];
      } else {
        out -= it->values[1];
      }
    } else if (it->flag == 2) {
      for (int j = 0; j < 4; j++) {
        if (j == 2) {
          continue;
        }
        out += it->values[j];
      }
    } else {
      out += classify_item(it);
    }
  }

  return out;
}

int main(void) {
  Container c;
  init_container(&c);

  mutate_alias(&c.items[0], &c.items[1]);
  mutate_alias(&c.items[2], &c.items[2]);

  long checksum = update_checksum(&c);
  int scan = scan_container(&c, 5);
  long walk = pointer_walk(&c);
  int branches = nested_branches(&c);

  printf("checksum=%ld\n", checksum);
  printf("scan=%d\n", scan);
  printf("walk=%ld\n", walk);
  printf("branches=%d\n", branches);

  if (scan > branches) {
    printf("scan-heavy %d\n", scan - branches);
  } else {
    printf("branch-heavy %d\n", branches - scan);
  }

  return 0;
}
