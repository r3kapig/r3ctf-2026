#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MOD 2281701377u
#define PRIMITIVE_ROOT 3
#define N 128

static uint32_t mod_pow(uint32_t base, uint64_t exp) {
    unsigned long long result = 1;
    unsigned long long cur = base % MOD;
    while (exp > 0) {
        if (exp & 1) {
            result = (result * cur) % MOD;
        }
        cur = (cur * cur) % MOD;
        exp >>= 1;
    }
    return (uint32_t)result;
}

static void ntt(uint32_t *a, int n, int invert) {
    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) {
            j ^= bit;
        }
        j ^= bit;
        if (i < j) {
            uint32_t tmp = a[i];
            a[i] = a[j];
            a[j] = tmp;
        }
    }

    for (int len = 2; len <= n; len <<= 1) {
        uint32_t wlen = mod_pow(PRIMITIVE_ROOT, (MOD - 1) / len);
        if (invert) {
            wlen = mod_pow(wlen, MOD - 2);
        }
        for (int i = 0; i < n; i += len) {
            uint32_t w = 1;
            for (int j = 0; j < len / 2; ++j) {
                uint32_t u = a[i + j];
                uint32_t v = (uint32_t)((unsigned long long)a[i + j + len / 2] * w % MOD);
                uint64_t add = (uint64_t)u + v;
                if (add >= MOD) {
                    add -= MOD;
                }
                uint64_t sub = (uint64_t)u + MOD - v;
                if (sub >= MOD) {
                    sub -= MOD;
                }
                a[i + j] = (uint32_t)add;
                a[i + j + len / 2] = (uint32_t)sub;
                w = (uint32_t)((unsigned long long)w * wlen % MOD);
            }
        }
    }

    if (invert) {
        uint32_t n_inv = mod_pow((uint32_t)n, MOD - 2);
        for (int i = 0; i < n; ++i) {
            a[i] = (uint32_t)((unsigned long long)a[i] * n_inv % MOD);
        }
    }
}

static void strtoul_line(char *buf, uint32_t *out) {
    uint32_t result = 0;
    for (size_t i = 0; buf[i] >= '0' && buf[i] <= '9'; i++) {
        if (i >= 11) {
            *out = 0;
            return;
        }
        result = result * 10 + (buf[i] - '0');
    }
    *out = result;
}

static size_t read_bytes(uint8_t *buf, size_t n) {
    size_t total = 0;
    for (; total < n; total++) {
        uint8_t c;
        ssize_t bytes_read = read(STDIN_FILENO, &c, 1);
        if (bytes_read <= 0) {
            break;
        }
        if (c == '\n') {
            break;
        }
        buf[total] = c;
    }
    return total;
}

static int read_uint32(uint32_t *out) {
    char buf[32];
    size_t bytes_read = read_bytes((uint8_t *)buf, sizeof(buf) - 2);
    if (bytes_read == 0) {
        return 0;
    }
    buf[bytes_read] = '\0';
    strtoul_line(buf, out);
    return 1;
}

static int scan_uint32(uint32_t *out) {
    return scanf("%u", out) == 1;
}

typedef struct {
    uint8_t degree;
    uint8_t sign;
    uint8_t reserved[2];
} degree_t;

#define PLOY_COUNT 0x40
#define U8_INDEX_COUNT 0x100
#define PLOY_ALIAS_INDEX (U8_INDEX_COUNT - 3)
#define PLOY_DEGREES_OFFSET \
    (PLOY_ALIAS_INDEX * (sizeof(uint32_t *) - sizeof(degree_t)))
#define PLOY_DEGREES_GAP \
    (PLOY_DEGREES_OFFSET - PLOY_COUNT * sizeof(uint32_t *))
#define PLOY_STORE_INIT_SIZE \
    (PLOY_DEGREES_OFFSET + PLOY_COUNT * sizeof(degree_t))

typedef struct {
    uint32_t *ploys[PLOY_COUNT];
    uint8_t degree_gap[PLOY_DEGREES_GAP];
    degree_t ploy_degrees[PLOY_COUNT];
} ploy_store_t;

ploy_store_t foo;

uint32_t **ploys = foo.ploys;
degree_t *ploy_degrees = foo.ploy_degrees;

static void init(void) {
    memset(&foo, 0, PLOY_STORE_INIT_SIZE);
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);
    setbuf(stdin, NULL);
}

static void read_poly(void) {
    uint32_t idx;
    uint32_t deg;

    if (!read_uint32(&idx)) {
        return;
    }
    if (idx >= PLOY_COUNT) {
        puts("Invalid index");
        return;
    }

    if (!read_uint32(&deg)) {
        return;
    }
    if (deg > 0x10) {
        puts("Invalid degree");
        return;
    }

    uint32_t *poly = malloc(N * sizeof(uint32_t));
    if (!poly) {
        puts("Allocation failed");
        return;
    }
    memset(poly, 0, N * sizeof(uint32_t));
    for (size_t i = 0; i < deg + 1; i++) {
        uint32_t coeff;
        if (!read_uint32(&coeff)) {
            coeff = 0;
        }
        poly[i] = coeff % MOD;
    }
    ploys[idx] = poly;
    ploy_degrees[idx] = (degree_t){.degree = (uint8_t)deg + 1};
    ntt(ploys[idx], N, 0);
}

static void multiply_polys(void) {
    uint32_t tmp;

    if (!read_uint32(&tmp)) {
        return;
    }
    uint8_t idx_a = (uint8_t)tmp;

    if (!read_uint32(&tmp)) {
        return;
    }
    uint8_t idx_dest = (uint8_t)tmp;

    if ((int8_t)idx_a >= PLOY_COUNT || (int8_t)idx_dest >= PLOY_COUNT || !ploys[idx_a]) {
        puts("Invalid indices");
        return;
    }

    uint32_t *f_dest = NULL;
    if (ploys[idx_dest]) {
        f_dest = ploys[idx_dest];
    } else {
        f_dest = malloc(N * sizeof(uint32_t));
        f_dest[0] = 1;
        ntt(f_dest, N, 0);
        ploy_degrees[idx_dest].degree = 1;
    }

    uint32_t *fa = ploys[idx_a];
    uint8_t deg_dest = (uint8_t)(ploy_degrees[idx_a].degree + ploy_degrees[idx_dest].degree - 1);
    for (int i = 0; i < N; ++i) {
        f_dest[i] = (uint32_t)((unsigned long long)fa[i] * f_dest[i] % MOD);
    }
    ploys[idx_dest] = f_dest;
    ploy_degrees[idx_dest].degree = deg_dest;
}

static void add_polys(void) {
    uint32_t idx_a;
    uint32_t idx_b;
    uint32_t idx_dest;

    if (!read_uint32(&idx_a) || !read_uint32(&idx_b) || !read_uint32(&idx_dest)) {
        return;
    }
    if (idx_a >= PLOY_COUNT || idx_b >= PLOY_COUNT || idx_dest >= PLOY_COUNT ||
        !ploys[idx_a] || !ploys[idx_b]) {
        puts("Invalid indices");
        return;
    }

    uint32_t *fa = ploys[idx_a];
    uint32_t *fb = ploys[idx_b];
    uint32_t *f_dest = NULL;
    if (ploys[idx_dest]) {
        f_dest = ploys[idx_dest];
    } else {
        f_dest = malloc(N * sizeof(uint32_t));
    }
    for (int i = 0; i < N; ++i) {
        uint64_t sum = (uint64_t)fa[i] + fb[i];
        if (sum >= MOD) {
            sum -= MOD;
        }
        f_dest[i] = (uint32_t)sum;
    }
    ploys[idx_dest] = f_dest;
    ploy_degrees[idx_dest] =
        (ploy_degrees[idx_a].degree > ploy_degrees[idx_b].degree) ? ploy_degrees[idx_a] : ploy_degrees[idx_b];
}

static void show_poly(void) {
    uint32_t ploy_tmp[N];
    uint32_t idx;

    if (!scan_uint32(&idx)) {
        return;
    }
    if (idx >= PLOY_COUNT || !ploys[idx]) {
        puts("Invalid index");
        return;
    }

    memcpy(ploy_tmp, ploys[idx], N * sizeof(uint32_t));
    ntt(ploy_tmp, N, 1);
    printf("Polynomial at index %u coefficients (mod %u):\n", idx, MOD);
    uint32_t deg = ploy_degrees[idx].degree > N ? N : ploy_degrees[idx].degree;
    for (size_t i = 0; i < deg; i++) {
        printf("%u ", ploy_tmp[i]);
    }
    puts("");
}

int main(void) {
    init();
    while (1) {
        uint32_t choice;
        if (!read_uint32(&choice)) {
            break;
        }
        switch (choice) {
            case 1:
                read_poly();
                break;
            case 2:
                multiply_polys();
                break;
            case 3:
                add_polys();
                break;
            case 4:
                show_poly();
                break;
            case 5:
                return 0;
            default:
                puts("Invalid choice");
                break;
        }
    }
    return 0;
}
