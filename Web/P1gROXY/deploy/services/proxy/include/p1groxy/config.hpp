#pragma once

#include <cstddef>
#include <string>

namespace p1groxy {

struct Config {
    std::string listen_host = "0.0.0.0";
    std::string listen_port = "8080";
    std::string upstream_host = "127.0.0.1";
    std::string upstream_port = "5001";
    std::size_t max_header_bytes = 64 * 1024;
    std::size_t max_body_bytes = 8 * 1024 * 1024;
    std::size_t cache_capacity_bytes = 8 * 1024 * 1024;
    std::size_t cache_max_object_bytes = 512 * 1024;
    int socket_timeout_seconds = 15;
    bool cache_enabled = true;
};

Config load_config_from_env();

}  // namespace p1groxy
