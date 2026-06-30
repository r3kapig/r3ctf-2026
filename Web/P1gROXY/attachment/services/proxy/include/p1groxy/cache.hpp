#pragma once

#include "p1groxy/http.hpp"

#include <cstddef>
#include <list>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>

namespace p1groxy {

struct CacheEntry {
    HttpResponse response;
    std::size_t bytes = 0;
};

class ResponseCache {
public:
    explicit ResponseCache(std::size_t capacity_bytes);

    std::optional<HttpResponse> get(const std::string& key);
    void put(const std::string& key, const HttpResponse& response);
    std::string make_key(const HttpRequest& request) const;

private:
    using ListIt = std::list<std::string>::iterator;

    struct Stored {
        CacheEntry entry;
        ListIt lru;
    };

    void evict_if_needed();

    std::size_t capacity_bytes_;
    std::size_t current_bytes_ = 0;
    std::list<std::string> lru_;
    std::unordered_map<std::string, Stored> entries_;
    mutable std::mutex mutex_;
};

}  // namespace p1groxy
