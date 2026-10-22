CC = gcc
CFLAGS = -Wall -Wextra -O2

main: main.c sorts.c sorts.h
	$(CC) $(CFLAGS) main.c sorts.c -o main

run: main
	./main

clean:
	rm -f main

.PHONY: run clean
