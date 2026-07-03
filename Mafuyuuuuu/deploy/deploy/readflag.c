#include <stdio.h>
#include <unistd.h>

int main(void) {
    if (setgid(0) != 0 || setuid(0) != 0) {
        return 1;
    }

    FILE *f = fopen("/flag", "r");
    if (f == NULL) {
        return 1;
    }

    char buf[256];
    while (fgets(buf, sizeof(buf), f) != NULL) {
        fputs(buf, stdout);
    }

    fclose(f);
    return 0;
}
