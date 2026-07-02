#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    char buf[4096];
    int fd = open("/flag", O_RDONLY);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    for (;;) {
        ssize_t n = read(fd, buf, sizeof(buf));
        if (n < 0) {
            perror("read");
            close(fd);
            return 1;
        }
        if (n == 0) {
            break;
        }
        if (write(STDOUT_FILENO, buf, (size_t)n) != n) {
            perror("write");
            close(fd);
            return 1;
        }
    }

    close(fd);
    return 0;
}
