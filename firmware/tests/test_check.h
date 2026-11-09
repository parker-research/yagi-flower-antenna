/*
 * Minimal test helpers. Each test executable returns non-zero if any CHECK failed.
 */
#pragma once

#include <math.h>
#include <stdbool.h>
#include <stdio.h>

static int test_check_failures = 0;

#define CHECK(condition, fmt, ...) \
    do { \
        if (!(condition)) { \
            test_check_failures++; \
            printf("FAIL %s:%d: %s -- " fmt "\n", __FILE__, __LINE__, #condition, ##__VA_ARGS__); \
        } \
    } while (0)

#define CHECK_NEAR(actual, expected, tolerance) \
    CHECK(fabsf((float)(actual) - (float)(expected)) <= (tolerance), \
          "got %.4f, expected %.4f", (double)(actual), (double)(expected))

#define TEST_CHECK_RESULT() \
    (printf("%s: %s\n", __FILE__, test_check_failures ? "FAILED" : "passed"), test_check_failures ? 1 : 0)
