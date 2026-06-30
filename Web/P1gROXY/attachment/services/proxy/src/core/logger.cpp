#include "p1groxy/logger.hpp"

#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>

namespace p1groxy {
namespace {

const char* level_name(LogLevel level) {
    switch (level) {
        case LogLevel::Info:
            return "INFO";
        case LogLevel::Warn:
            return "WARN";
        case LogLevel::Error:
            return "ERROR";
    }
    return "INFO";
}

std::string utc_now() {
    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    gmtime_r(&t, &tm);
    std::ostringstream out;
    out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}

}  // namespace

void Logger::log(LogLevel level, const std::string& message) {
    std::lock_guard<std::mutex> guard(mutex_);
    std::cerr << utc_now() << " " << level_name(level) << " " << message << "\n";
}

Logger& logger() {
    static Logger instance;
    return instance;
}

}  // namespace p1groxy
