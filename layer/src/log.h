#pragma once
#include <cstdarg>
#include <cstdio>

namespace chuds_fg {

enum class LogLevel { Error = 0, Warn = 1, Info = 2, Debug = 3 };

void log_set_level(int level);
int  log_get_level();
void log_set_file(const char* path);
#if defined(__GNUC__)
void log_write(LogLevel lvl, const char* fmt, ...) __attribute__((format(printf, 2, 3)));
#else
void log_write(LogLevel lvl, const char* fmt, ...);
#endif

} // namespace chuds_fg

#define CHUDS_FG_LOG(lvl, ...)  ::chuds_fg::log_write(::chuds_fg::LogLevel::lvl, __VA_ARGS__)
#define CHUDS_FG_ERR(...)       CHUDS_FG_LOG(Error, __VA_ARGS__)
#define CHUDS_FG_WARN(...)      CHUDS_FG_LOG(Warn, __VA_ARGS__)
#define CHUDS_FG_INFO(...)      CHUDS_FG_LOG(Info, __VA_ARGS__)
#define CHUDS_FG_DBG(...)       CHUDS_FG_LOG(Debug, __VA_ARGS__)
