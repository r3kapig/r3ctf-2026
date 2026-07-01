#include "p1groxy/config.hpp"

#include <cstdlib>
#include <string>

namespace p1groxy {
namespace {

std::string env_or(const char* name, const char* fallback) {
    const char* value = std::getenv(name);
    return value && *value ? std::string(value) : std::string(fallback);
}

std::size_t size_env_or(const char* name, std::size_t fallback) {
    const char* value = std::getenv(name);
    if (!value || !*value) {
        return fallback;
    }
    char* end = nullptr;
    unsigned long long parsed = std::strtoull(value, &end, 10);
    if (!end || *end != '\0' || parsed == 0) {
        return fallback;
    }
    return static_cast<std::size_t>(parsed);
}

int int_env_or(const char* name, int fallback) {
    const char* value = std::getenv(name);
    if (!value || !*value) {
        return fallback;
    }
    char* end = nullptr;
    long parsed = std::strtol(value, &end, 10);
    if (!end || *end != '\0' || parsed <= 0) {
        return fallback;
    }
    return static_cast<int>(parsed);
}

bool bool_env_or(const char* name, bool fallback) {
    const char* value = std::getenv(name);
    if (!value || !*value) {
        return fallback;
    }
    std::string v(value);
    return v == "1" || v == "true" || v == "yes" || v == "on";
}

}  // namespace

Config load_config_from_env() {
    Config cfg;
    cfg.listen_host = env_or("P1GROXY_LISTEN_HOST", "0.0.0.0");
    cfg.listen_port = env_or("P1GROXY_LISTEN_PORT", "8080");
    cfg.upstream_host = env_or("P1GROXY_UPSTREAM_HOST", "127.0.0.1");
    cfg.upstream_port = env_or("P1GROXY_UPSTREAM_PORT", "5001");
    cfg.max_header_bytes = size_env_or("P1GROXY_MAX_HEADER_BYTES", cfg.max_header_bytes);
    cfg.max_body_bytes = size_env_or("P1GROXY_MAX_BODY_BYTES", cfg.max_body_bytes);
    cfg.cache_capacity_bytes = size_env_or("P1GROXY_CACHE_CAPACITY_BYTES", cfg.cache_capacity_bytes);
    cfg.cache_max_object_bytes = size_env_or("P1GROXY_CACHE_MAX_OBJECT_BYTES", cfg.cache_max_object_bytes);
    cfg.socket_timeout_seconds = int_env_or("P1GROXY_SOCKET_TIMEOUT_SECONDS", cfg.socket_timeout_seconds);
    cfg.cache_enabled = bool_env_or("P1GROXY_CACHE_ENABLED", cfg.cache_enabled);
    return cfg;
}

}  // namespace p1groxy
