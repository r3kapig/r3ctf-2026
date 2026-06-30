#include "p1groxy/cache.hpp"
#include "p1groxy/config.hpp"
#include "p1groxy/content_coding.hpp"
#include "p1groxy/http.hpp"
#include "p1groxy/logger.hpp"
#include "p1groxy/policy.hpp"
#include "p1groxy/socket.hpp"

#include <atomic>
#include <cerrno>
#include <csignal>
#include <cstring>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include <arpa/inet.h>
#include <netdb.h>
#include <strings.h>
#include <sys/socket.h>
#include <unistd.h>

namespace p1groxy {
namespace {

std::atomic<bool> g_running{true};
std::atomic<int> g_listener_fd{-1};

std::string peer_address(const sockaddr_storage& addr) {
    char host[NI_MAXHOST] = {0};
    if (getnameinfo(reinterpret_cast<const sockaddr*>(&addr), sizeof(addr),
                    host, sizeof(host), nullptr, 0, NI_NUMERICHOST) != 0) {
        return "unknown";
    }
    return host;
}

void send_response(int fd, HttpResponse response, const Config& cfg) {
    bool should_normalize_body = true;
    if (response.has_policy_body) {
        HttpResponse policy_view = response;
        policy_view.body = response.policy_body;
        should_normalize_body = normalize_response_body_for_client(policy_view, cfg.upstream_host, cfg.upstream_port);
    }
    if (should_normalize_body) {
        normalize_response_body_for_client(response, cfg.upstream_host, cfg.upstream_port);
    }
    normalize_response_for_client(response);
    auto bytes = serialize_response(response);
    write_all(fd, bytes);
}

void maybe_decode_request(ContentCoding& coding, HttpRequest& request) {
    auto encoding = header_value(request.headers, "Content-Encoding");
    if (!encoding || strcasecmp(encoding->c_str(), "identity") == 0) {
        return;
    }
    request.body = coding.decode(*encoding, request.body);
    erase_header(request.headers, "Content-Encoding");
    set_header(request.headers, "Content-Length", std::to_string(request.body.size()));
}

void maybe_decode_response(ContentCoding& coding, HttpResponse& response) {
    auto encoding = header_value(response.headers, "Content-Encoding");
    if (!encoding || strcasecmp(encoding->c_str(), "identity") == 0) {
        return;
    }
    if (response.chunked && has_token_header(response.headers, "Transfer-Encoding", "chunked")) {
        std::vector<std::uint8_t> policy_body;
        policy_body.reserve(response.body.size() * 2);
        for (const auto& fragment : response.transfer_chunks) {
            auto part = coding.decode_transfer_fragment(*encoding, fragment);
            policy_body.insert(policy_body.end(), part.begin(), part.end());
        }
        response.policy_body = std::move(policy_body);
        response.has_policy_body = !response.policy_body.empty();
        response.body = coding.decode(*encoding, response.body);
        response.transfer_chunks.clear();
        response.chunked = false;
        erase_header(response.headers, "Transfer-Encoding");
        erase_header(response.headers, "Content-Encoding");
        set_header(response.headers, "Content-Length", std::to_string(response.body.size()));
        return;
    }
    response.body = coding.decode(*encoding, response.body);
    erase_header(response.headers, "Content-Encoding");
    set_header(response.headers, "Content-Length", std::to_string(response.body.size()));
}

HttpResponse fetch_upstream(const Config& cfg, const HttpRequest& request) {
    UniqueFd upstream = connect_tcp(cfg.upstream_host, cfg.upstream_port, cfg.socket_timeout_seconds);
    auto outbound = serialize_request(request);
    write_all(upstream.get(), outbound);
    return read_http_response(upstream.get(), ReadLimits{cfg.max_header_bytes, cfg.max_body_bytes * 2});
}

void handle_client(UniqueFd client, sockaddr_storage peer, Config cfg, std::shared_ptr<ResponseCache> cache) {
    set_socket_timeout(client.get(), cfg.socket_timeout_seconds);
    ContentCoding coding;
    std::string peer_ip = peer_address(peer);

    for (;;) {
        HttpRequest request;
        try {
            request = read_http_request(client.get(), ReadLimits{cfg.max_header_bytes, cfg.max_body_bytes});
        } catch (const std::exception& e) {
            if (std::string(e.what()).find("connection closed") == std::string::npos) {
                logger().log(LogLevel::Warn, peer_ip + " bad request: " + e.what());
                send_response(client.get(), text_response(400, "Bad Request", "request could not be processed\n"), cfg);
            }
            break;
        }

        bool close_after = request.version == "HTTP/1.0" || has_token_header(request.headers, "Connection", "close");
        std::string access_target = request.target;

        try {
            maybe_decode_request(coding, request);
        } catch (const std::exception& e) {
            logger().log(LogLevel::Warn, peer_ip + " request content coding failed: " + e.what());
            send_response(client.get(), text_response(415, "Unsupported Media Type", "unsupported encoded request body\n"), cfg);
            break;
        }

        normalize_request_for_upstream(request, cfg.upstream_host, cfg.upstream_port, peer_ip);

        std::string cache_key;
        if (cfg.cache_enabled && request.method == "GET") {
            cache_key = cache->make_key(request);
            if (auto cached = cache->get(cache_key)) {
                set_header(cached->headers, "X-P1gROXY-Cache", "hit");
                send_response(client.get(), *cached, cfg);
                logger().log(LogLevel::Info, peer_ip + " " + request.method + " " + access_target + " 200 cache=hit");
                if (close_after) {
                    break;
                }
                continue;
            }
        }

        HttpResponse response;
        try {
            response = fetch_upstream(cfg, request);
            maybe_decode_response(coding, response);
        } catch (const std::exception& e) {
            logger().log(LogLevel::Error, peer_ip + " upstream failure: " + e.what());
            send_response(client.get(), text_response(502, "Bad Gateway", "upstream request failed\n"), cfg);
            break;
        }

        if (cfg.cache_enabled && !cache_key.empty() && cacheable_response(request, response, cfg.cache_max_object_bytes)) {
            cache->put(cache_key, response);
            set_header(response.headers, "X-P1gROXY-Cache", "store");
        } else {
            set_header(response.headers, "X-P1gROXY-Cache", "bypass");
        }

        int status = response.status;
        send_response(client.get(), response, cfg);
        logger().log(LogLevel::Info, peer_ip + " " + request.method + " " + access_target + " " +
                                     std::to_string(status) + " cache=" + (cache_key.empty() ? "bypass" : "miss"));
        if (close_after) {
            break;
        }
    }
}

void on_signal(int) {
    g_running.store(false);
    int fd = g_listener_fd.load();
    if (fd >= 0) {
        close(fd);
    }
}

}  // namespace
}  // namespace p1groxy

int main() {
    using namespace p1groxy;
    std::signal(SIGPIPE, SIG_IGN);
    std::signal(SIGINT, on_signal);
    std::signal(SIGTERM, on_signal);

    try {
        Config cfg = load_config_from_env();
        auto cache = std::make_shared<ResponseCache>(cfg.cache_capacity_bytes);
        UniqueFd listener = listen_tcp(cfg.listen_host, cfg.listen_port, 128);
        g_listener_fd.store(listener.get());
        logger().log(LogLevel::Info, "P1gROXY listening on " + cfg.listen_host + ":" + cfg.listen_port +
                                      " -> " + cfg.upstream_host + ":" + cfg.upstream_port);

        while (g_running.load()) {
            sockaddr_storage peer{};
            socklen_t peer_len = sizeof(peer);
            int fd = accept(listener.get(), reinterpret_cast<sockaddr*>(&peer), &peer_len);
            if (fd < 0) {
                if (errno == EINTR) {
                    continue;
                }
                logger().log(LogLevel::Warn, "accept failed");
                continue;
            }
            std::thread(handle_client, UniqueFd(fd), peer, cfg, cache).detach();
        }
        g_listener_fd.store(-1);
    } catch (const std::exception& e) {
        logger().log(LogLevel::Error, e.what());
        return 1;
    }
    return 0;
}
