/*
 * Minimal freestanding devmem for ARM EABI Linux (no libc).
 *   devmem <addr> [count]        dump <count> 32-bit words (default 1)
 *   devmem -w <addr> <value>     write one 32-bit word
 * Build: clang --target=armv7a-linux-gnueabi -march=armv7-a -marm -Os \
 *        -ffreestanding -fno-stack-protector -nostdlib -static \
 *        -fuse-ld=lld -o devmem devmem.c
 */
typedef unsigned int u32;
typedef unsigned long ul;

static long sys(long n, long a, long b, long c, long d, long e, long f)
{
	register long r7 asm("r7") = n;
	register long r0 asm("r0") = a;
	register long r1 asm("r1") = b;
	register long r2 asm("r2") = c;
	register long r3 asm("r3") = d;
	register long r4 asm("r4") = e;
	register long r5 asm("r5") = f;
	asm volatile("svc 0" : "+r"(r0) : "r"(r7), "r"(r1), "r"(r2), "r"(r3),
		     "r"(r4), "r"(r5) : "memory");
	return r0;
}
#define SYS_exit 1
#define SYS_write 4
#define SYS_open 5
#define SYS_mmap2 192

static void out(const char *s, int n) { sys(SYS_write, 1, (long)s, n, 0, 0, 0); }
static void puts_(const char *s) { int n = 0; while (s[n]) n++; out(s, n); }
static void die(const char *s) { puts_(s); puts_("\n"); sys(SYS_exit, 1, 0, 0, 0, 0, 0); }

static ul parse(const char *s)
{
	ul v = 0; int base = 10;
	if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) { base = 16; s += 2; }
	for (; *s; s++) {
		int d;
		if (*s >= '0' && *s <= '9') d = *s - '0';
		else if (*s >= 'a' && *s <= 'f') d = *s - 'a' + 10;
		else if (*s >= 'A' && *s <= 'F') d = *s - 'A' + 10;
		else break;
		if (d >= base) break;
		v = v * base + d;
	}
	return v;
}

static void hex(u32 v, char *b) { for (int i = 7; i >= 0; i--) { b[i] = "0123456789abcdef"[v & 15]; v >>= 4; } }

static int run(int argc, char **argv)
{
	int wr = argc > 1 && argv[1][0] == '-' && argv[1][1] == 'w';
	if (argc < 2 || (wr && argc < 4)) die("usage: devmem <addr> [count] | devmem -w <addr> <val>");
	ul addr = parse(argv[wr ? 2 : 1]);
	ul cnt = wr ? 1 : (argc > 2 ? parse(argv[2]) : 1);
	long fd = sys(SYS_open, (long)"/dev/mem", 02 | 010000 /* O_RDWR|O_SYNC */, 0, 0, 0, 0);
	if (fd < 0) die("open /dev/mem failed");
	ul base = addr & ~0xfffUL, off = addr - base;
	ul len = (off + cnt * 4 + 0xfff) & ~0xfffUL;
	long m = sys(SYS_mmap2, 0, len, 3 /* RW */, 1 /* SHARED */, fd, base >> 12);
	if ((ul)m > 0xfffff000UL) die("mmap failed");
	volatile u32 *p = (volatile u32 *)(m + off);
	if (wr) { *p = parse(argv[3]); cnt = 1; }
	char line[20];
	for (ul i = 0; i < cnt; i++) {
		hex(addr + i * 4, line); line[8] = ':'; line[9] = ' ';
		hex(p[i], line + 10); line[18] = '\n';
		out(line, 19);
	}
	return 0;
}

__attribute__((naked, noreturn)) void _start(void)
{
	asm volatile("mov r0, sp\n"
		     "bl cstart\n");
}

__attribute__((used, noreturn)) void cstart(long *sp)
{
	int argc = (int)sp[0];
	char **argv = (char **)(sp + 1);
	sys(SYS_exit, run(argc, argv), 0, 0, 0, 0, 0);
	for (;;);
}
