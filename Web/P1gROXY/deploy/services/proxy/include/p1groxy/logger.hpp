#pragma once

#include <mutex>
#include <string>

namespace p1groxy {

enum class LogLevel {
    Info,
    Warn,
    Error,
};

class Logger {
public:
    void log(LogLevel level, const std::string& message);

private:
    std::mutex mutex_;
};

Logger& logger();

}  // namespace p1groxy
