#include "p1groxy/policy.hpp"

#include <algorithm>
#include <cctype>
#include <cstring>
#include <optional>
#include <string>
#include <vector>

namespace p1groxy {
namespace {

void remove_hop_by_hop(HeaderMap& headers) {
    erase_header(headers, "Connection");
    erase_header(headers, "Proxy-Connection");
    erase_header(headers, "Transfer-Encoding");
    erase_header(headers, "TE");
    erase_header(headers, "Trailer");
    erase_header(headers, "Upgrade");
    erase_header(headers, "Keep-Alive");
}

std::string lower_ascii(std::string input) {
    std::transform(input.begin(), input.end(), input.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return input;
}

bool is_html_response(const HttpResponse& response) {
    auto type = header_value(response.headers, "Content-Type");
    return type && lower_ascii(*type).find("text/html") != std::string::npos;
}

bool starts_with(const std::string& value, const std::string& prefix) {
    return value.size() >= prefix.size() &&
           std::equal(prefix.begin(), prefix.end(), value.begin());
}

std::string escape_attribute_value(const std::string& value) {
    std::string out;
    out.resize(value.size());
    char* write = out.data();

    for (unsigned char c : value) {
        switch (c) {
            case '&':
                std::memcpy(write, "&amp;", 5);
                write += 5;
                break;
            case '"':
                std::memcpy(write, "&quot;", 6);
                write += 6;
                break;
            case '<':
                std::memcpy(write, "&lt;", 4);
                write += 4;
                break;
            case '>':
                std::memcpy(write, "&gt;", 4);
                write += 4;
                break;
            default:
                *write++ = static_cast<char>(c);
                break;
        }
    }

    out.resize(static_cast<std::size_t>(write - out.data()));
    return out;
}

std::string private_origin_prefix(const std::string& upstream_host, const std::string& upstream_port) {
    return "http://" + upstream_host + ":" + upstream_port;
}

std::optional<std::string> public_origin_path(const std::string& value, const std::string& origin) {
    if (!starts_with(value, origin)) {
        return std::nullopt;
    }
    std::string path = value.substr(origin.size());
    if (path.empty()) {
        path = "/";
    }
    if (path[0] != '/') {
        path.insert(path.begin(), '/');
    }
    return escape_attribute_value(path);
}

bool rewrite_attribute(std::string& html,
                       const std::string& lowered_pattern,
                       const std::string& origin) {
    std::string lowered = lower_ascii(html);
    std::size_t pos = 0;
    char quote = lowered_pattern.back();
    bool changed = false;

    while ((pos = lowered.find(lowered_pattern, pos)) != std::string::npos) {
        std::size_t value_begin = pos + lowered_pattern.size();
        std::size_t value_end = html.find(quote, value_begin);
        if (value_end == std::string::npos) {
            break;
        }

        std::string value = html.substr(value_begin, value_end - value_begin);
        if (auto replacement = public_origin_path(value, origin)) {
            html.replace(value_begin, value.size(), *replacement);
            lowered = lower_ascii(html);
            pos = value_begin + replacement->size();
            changed = true;
        } else {
            pos = value_end + 1;
        }
    }
    return changed;
}

}  // namespace

void normalize_request_for_upstream(HttpRequest& request,
                                    const std::string& upstream_host,
                                    const std::string& upstream_port,
                                    const std::string& client_addr) {
    request.target = origin_form_target(request.target);
    remove_hop_by_hop(request.headers);
    set_header(request.headers, "Host", upstream_host + ":" + upstream_port);
    set_header(request.headers, "Connection", "close");
    set_header(request.headers, "X-Forwarded-For", client_addr);
    set_header(request.headers, "X-Forwarded-Proto", "http");
    set_header(request.headers, "X-P1gROXY-Edge", "canonical");
    set_header(request.headers, "Content-Length", std::to_string(request.body.size()));
}

bool normalize_response_body_for_client(HttpResponse& response,
                                        const std::string& upstream_host,
                                        const std::string& upstream_port) {
    if (!is_html_response(response) || response.body.empty()) {
        return false;
    }

    std::string html(response.body.begin(), response.body.end());
    std::string origin = private_origin_prefix(upstream_host, upstream_port);
    bool changed = false;
    for (const char* attr : {"href", "src", "action"}) {
        changed = rewrite_attribute(html, std::string(attr) + "=\"", origin) || changed;
        changed = rewrite_attribute(html, std::string(attr) + "='", origin) || changed;
    }
    if (!changed) {
        return false;
    }
    response.body.assign(html.begin(), html.end());
    return true;
}

void normalize_response_for_client(HttpResponse& response) {
    remove_hop_by_hop(response.headers);
    erase_header(response.headers, "Server");
    set_header(response.headers, "Content-Length", std::to_string(response.body.size()));
    if (!header_value(response.headers, "X-Content-Type-Options")) {
        set_header(response.headers, "X-Content-Type-Options", "nosniff");
    }
    if (!header_value(response.headers, "Referrer-Policy")) {
        set_header(response.headers, "Referrer-Policy", "same-origin");
    }
    if (!header_value(response.headers, "X-Frame-Options")) {
        set_header(response.headers, "X-Frame-Options", "DENY");
    }
    set_header(response.headers, "Connection", "keep-alive");
}

}  // namespace p1groxy
