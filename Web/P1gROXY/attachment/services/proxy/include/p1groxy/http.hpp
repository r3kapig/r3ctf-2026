#pragma once

#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace p1groxy {

using HeaderMap = std::map<std::string, std::string, std::less<>>;

struct HttpRequest {
    std::string method;
    std::string target;
    std::string version;
    HeaderMap headers;
    std::vector<std::uint8_t> body;
};

struct HttpResponse {
    std::string version = "HTTP/1.1";
    int status = 200;
    std::string reason = "OK";
    HeaderMap headers;
    std::vector<std::uint8_t> body;
    std::vector<std::vector<std::uint8_t>> transfer_chunks;
    std::vector<std::uint8_t> policy_body;
    bool has_policy_body = false;
    bool chunked = false;
};

struct ReadLimits {
    std::size_t max_header_bytes;
    std::size_t max_body_bytes;
};

std::optional<std::string> header_value(const HeaderMap& headers, std::string_view name);
void set_header(HeaderMap& headers, const std::string& name, const std::string& value);
void erase_header(HeaderMap& headers, std::string_view name);
bool has_token_header(const HeaderMap& headers, std::string_view name, std::string_view token);

HttpRequest read_http_request(int fd, const ReadLimits& limits);
HttpResponse read_http_response(int fd, const ReadLimits& limits);

std::vector<std::uint8_t> serialize_request(const HttpRequest& request);
std::vector<std::uint8_t> serialize_response(const HttpResponse& response);
HttpResponse text_response(int status, const std::string& reason, const std::string& body);

std::string origin_form_target(const std::string& target);
bool cacheable_response(const HttpRequest& request, const HttpResponse& response, std::size_t max_object);

}  // namespace p1groxy
