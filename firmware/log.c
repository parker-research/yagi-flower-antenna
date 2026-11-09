#include "log.h"

volatile log_level_t log_level = LOG_ALWAYS;

const char *log_level_name(log_level_t level) {
    switch (level) {
        case LOG_ALWAYS: return "ALWAYS";
        case LOG_INFO:   return " INFO ";
        case LOG_DEBUG:  return "DEBUG ";
        case LOG_TRACE:  return "TRACE ";
    }
    return "UNKNOWN";
}
