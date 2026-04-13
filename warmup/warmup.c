// warmup.c — toolchain validation binary (10 functions)
// macOS:   gcc -O0 -o warmup warmup.c && strip warmup
// Linux:   gcc -O0 -o warmup warmup.c && strip warmup
// Windows: gcc -O0 -o warmup.exe warmup.c && strip warmup.exe
//          (gcc via MSYS2, or: cl /Od warmup.c)
// NOTE: -O0 is intentional — optimization inlines functions,
//       which defeats the purpose of this toolchain validation.
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int add(int a, int b) { return a + b; }
int multiply(int a, int b) { return a * b; }
void greet(const char *name) { printf("Hello, %s\n", name); }
int fibonacci(int n) { return n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2); }
char *reverse_string(const char *s) {
    int len = strlen(s);
    char *r = malloc(len + 1);
    for (int i = 0; i < len; i++) r[i] = s[len - 1 - i];
    r[len] = '\0';
    return r;
}
int max_val(int a, int b) { return a > b ? a : b; }
int min_val(int a, int b) { return a < b ? a : b; }
int sum_to(int n) {
    int s = 0;
    for (int i = 1; i <= n; i++) s += i;
    return s;
}
void process(int mode, const char *input) {
    if (mode == 1) greet(input);
    else if (mode == 2) { char *r = reverse_string(input); printf("%s\n", r); free(r); }
    else printf("fib(10) = %d, 3+4 = %d, 3*4 = %d, max(5,3) = %d, sum(10) = %d\n",
                fibonacci(10), add(3,4), multiply(3,4), max_val(5,3), sum_to(10));
}
int main(int argc, char **argv) {
    process(argc > 1 ? atoi(argv[1]) : 0, argc > 2 ? argv[2] : "world");
    return 0;
}
