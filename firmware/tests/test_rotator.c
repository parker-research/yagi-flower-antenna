/*
 * Easycomm II parser tests: the exact strings hamlib's easycomm2 driver sends,
 * and the replies it expects.
 */
#include <string.h>
#include <unistd.h>

#include "controller.h"
#include "rotator.h"
#include "test_check.h"

// ---------------------------------------------------------------------------
// Fake controller: records what the rotator parser sets.
// ---------------------------------------------------------------------------
static float s_target_az_deg = 0.0f, s_target_el_deg = 90.0f;
static int s_set_target_calls = 0;

void controller_set_target(float az_deg, float el_deg) {
    s_target_az_deg = az_deg;
    s_target_el_deg = el_deg;
    s_set_target_calls++;
}

void controller_get_target(float *az_deg, float *el_deg) {
    *az_deg = s_target_az_deg;
    *el_deg = s_target_el_deg;
}

// ---------------------------------------------------------------------------
// Run one line through the parser, capturing what it prints to stdout.
// ---------------------------------------------------------------------------
static char s_reply[256];

static bool run_line(const char *line) {
    char line_copy[128];
    strcpy(line_copy, line);

    int pipe_fds[2];
    fflush(stdout);
    const int saved_stdout = dup(STDOUT_FILENO);
    if (pipe(pipe_fds) != 0) return false;
    dup2(pipe_fds[1], STDOUT_FILENO);

    const bool recognised = rotator_handle_line(line_copy);

    fflush(stdout);
    dup2(saved_stdout, STDOUT_FILENO);
    close(saved_stdout);
    close(pipe_fds[1]);
    const ssize_t length = read(pipe_fds[0], s_reply, sizeof(s_reply) - 1);
    s_reply[length > 0 ? length : 0] = '\0';
    close(pipe_fds[0]);
    return recognised;
}

#define CHECK_LINE(line, expected_recognised, expected_reply) \
    do { \
        const bool recognised = run_line(line); \
        CHECK(recognised == (expected_recognised), "line '%s'", line); \
        CHECK(strcmp(s_reply, expected_reply) == 0, "line '%s': reply '%s', expected '%s'", line, s_reply, expected_reply); \
    } while (0)

static void reset_target(float az_deg, float el_deg) {
    s_target_az_deg = az_deg;
    s_target_el_deg = el_deg;
    s_set_target_calls = 0;
}

static void test_get_position(void) {
    reset_target(123.4f, 45.0f);
    CHECK_LINE("AZ EL ", true, "AZ123.4 EL45.0\n");   // hamlib easycomm2 get_position
    CHECK_LINE("AZ EL", true, "AZ123.4 EL45.0\n");
    CHECK_LINE("AZ", true, "AZ123.4\n");
    CHECK_LINE("EL", true, "EL45.0\n");
    CHECK(s_set_target_calls == 0, "queries must not set the target");
}

static void test_set_position(void) {
    reset_target(0.0f, 0.0f);
    CHECK_LINE("AZ123.4 EL45.0", true, "");             // hamlib easycomm2 set_position
    CHECK(s_set_target_calls == 1, "calls=%d", s_set_target_calls);
    CHECK_NEAR(s_target_az_deg, 123.4f, 1e-4f);
    CHECK_NEAR(s_target_el_deg, 45.0f, 1e-4f);

    // Single axis keeps the other.
    CHECK_LINE("AZ200", true, "");
    CHECK_NEAR(s_target_az_deg, 200.0f, 1e-4f);
    CHECK_NEAR(s_target_el_deg, 45.0f, 1e-4f);

    // Easycomm I form, with uplink/downlink fields.
    CHECK_LINE("AZ10.0 EL20.0 UP000 XXX DN000 XXX", true, "");
    CHECK_NEAR(s_target_az_deg, 10.0f, 1e-4f);
    CHECK_NEAR(s_target_el_deg, 20.0f, 1e-4f);

    // Negative and > 360 values are passed through unchanged (selection handles wrap).
    CHECK_LINE("AZ-10.5 EL0", true, "");
    CHECK_NEAR(s_target_az_deg, -10.5f, 1e-4f);
}

static void test_set_then_get_on_one_line(void) {
    reset_target(0.0f, 0.0f);
    CHECK_LINE("AZ90.0 EL30.0 AZ EL", true, "AZ90.0 EL30.0\n");
}

static void test_other_commands(void) {
    reset_target(1.0f, 2.0f);
    CHECK_LINE("VE", true, "VEyagi-flower-test\n");
    CHECK_LINE("SA SE ", true, "");                     // hamlib stop
    CHECK_LINE("MU", true, "");
    CHECK(s_set_target_calls == 0, "stop/move must not set the target");
}

static void test_rejects_garbage(void) {
    reset_target(1.0f, 2.0f);
    CHECK_LINE("FOO", false, "");
    CHECK_LINE("AZbad", false, "");
    CHECK_LINE("AZ12x", false, "");
    CHECK(s_set_target_calls == 0, "garbage must not set the target");
    CHECK_NEAR(s_target_az_deg, 1.0f, 1e-4f);
}

int main(void) {
    test_get_position();
    test_set_position();
    test_set_then_get_on_one_line();
    test_other_commands();
    test_rejects_garbage();
    return TEST_CHECK_RESULT();
}
