#include "p1groxy/cache.hpp"

#include <utility>

namespace p1groxy {

ResponseCache::ResponseCache(std::size_t capacity_bytes) : capacity_bytes_(capacity_bytes) {}

std::optional<HttpResponse> ResponseCache::get(const std::string& key) {
    std::lock_guard<std::mutex> guard(mutex_);
    auto it = entries_.find(key);
    if (it == entries_.end()) {
        return std::nullopt;
    }
    lru_.erase(it->second.lru);
    lru_.push_front(key);
    it->second.lru = lru_.begin();
    return it->second.entry.response;
}

void ResponseCache::put(const std::string& key, const HttpResponse& response) {
    std::lock_guard<std::mutex> guard(mutex_);
    std::size_t bytes = response.body.size();
    if (bytes > capacity_bytes_) {
        return;
    }
    auto existing = entries_.find(key);
    if (existing != entries_.end()) {
        current_bytes_ -= existing->second.entry.bytes;
        lru_.erase(existing->second.lru);
        entries_.erase(existing);
    }
    lru_.push_front(key);
    entries_[key] = Stored{CacheEntry{response, bytes}, lru_.begin()};
    current_bytes_ += bytes;
    evict_if_needed();
}

std::string ResponseCache::make_key(const HttpRequest& request) const {
    auto accept = header_value(request.headers, "Accept");
    return request.method + " " + origin_form_target(request.target) + " accept=" + accept.value_or("*");
}

void ResponseCache::evict_if_needed() {
    while (current_bytes_ > capacity_bytes_ && !lru_.empty()) {
        std::string victim = lru_.back();
        lru_.pop_back();
        auto it = entries_.find(victim);
        if (it != entries_.end()) {
            current_bytes_ -= it->second.entry.bytes;
            entries_.erase(it);
        }
    }
}

}  // namespace p1groxy
