// warmup.c — toolchain validation binary
// macOS:   gcc -O2 -o warmup warmup.c && strip warmup
// Linux:   gcc -O2 -o warmup warmup.c && strip warmup
// Windows: gcc -O2 -o warmup.exe warmup.c && strip warmup.exe
//          (gcc via MSYS2, or: cl /O2 warmup.c)
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int add(int a, int b) { return a + b; }
static int multiply(int a, int b) { return a * b; }
static void greet(const char *name) { printf("Hello, %s\n", name); }
static int fibonacci(int n) { return n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2); }
static char *reverse_string(const char *s) {
    int len = strlen(s);
    char *r = malloc(len + 1);
    for (int i = 0; i < len; i++) r[i] = s[len - 1 - i];
    r[len] = '\0';
    return r;
}
static void process(int mode, const char *input) {
    if (mode == 1) greet(input);
    else if (mode == 2) { char *r = reverse_string(input); printf("%s\n", r); free(r); }
    else printf("fib(10) = %d, 3+4 = %d, 3*4 = %d\n", fibonacci(10), add(3,4), multiply(3,4));
}
int main(int argc, char **argv) {
    process(argc > 1 ? atoi(argv[1]) : 0, argc > 2 ? argv[2] : "world");
    return 0;
}
