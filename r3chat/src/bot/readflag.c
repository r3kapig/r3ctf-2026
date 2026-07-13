#include <stdio.h>
#include <unistd.h>

int main(void) {
  setgid(0);
  setuid(0);
  FILE *f = fopen("/flag", "r");
  if (!f) {
    perror("open /flag");
    return 1;
  }
  char buf[512];
  size_t n;
  while ((n = fread(buf, 1, sizeof buf, f)) > 0) fwrite(buf, 1, n, stdout);
  fclose(f);
  return 0;
}
