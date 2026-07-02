#include "p1groxy/http.hpp"
#include "p1groxy/socket.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <charconv>
#include <cerrno>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unistd.h>

namespace p1groxy {
namespace {

std::string lower(std::string_view input) {
    std::string out(input);
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return out;
}

std::string trim(std::string_view input) {
    std::size_t begin = 0;
    while (begin < input.size() && std::isspace(static_cast<unsigned char>(input[begin]))) {
        begin++;
    }
    std::size_t end = input.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(input[end - 1]))) {
        end--;
    }
    return std::string(input.substr(begin, end - begin));
}

std::size_t parse_content_length(const HeaderMap& headers) {
    auto value = header_value(headers, "Content-Length");
    if (!value) {
        return 0;
    }
    std::size_t out = 0;
    auto begin = value->data();
    auto end = value->data() + value->size();
    auto result = std::from_chars(begin, end, out);
    if (result.ec != std::errc{} || result.ptr != end) {
        throw std::runtime_error("invalid Content-Length");
    }
    return out;
}

std::vector<std::uint8_t> read_http_message_bytes(int fd, const ReadLimits& limits, std::size_t& header_len) {
    std::vector<std::uint8_t> raw;
    raw.reserve(8192);
    std::array<char, 8192> chunk{};
    auto find_end = [&]() -> std::optional<std::size_t> {
        if (raw.size() < 4) {
            return std::nullopt;
        }
        for (std::size_t i = 0; i + 3 < raw.size(); i++) {
            if (raw[i] == '\r' && raw[i + 1] == '\n' && raw[i + 2] == '\r' && raw[i + 3] == '\n') {
                return i + 4;
            }
        }
        return std::nullopt;
    };

    for (;;) {
        if (auto end = find_end()) {
            header_len = *end;
            break;
        }
        if (raw.size() > limits.max_header_bytes) {
            throw std::runtime_error("header block too large");
        }
        ssize_t n = read(fd, chunk.data(), chunk.size());
        if (n == 0) {
            throw std::runtime_error("connection closed while reading headers");
        }
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            throw std::runtime_error("read failed while reading headers");
        }
        raw.insert(raw.end(), chunk.data(), chunk.data() + n);
    }
    return raw;
}

HeaderMap parse_headers(const std::string& block, std::size_t first_line_end) {
    HeaderMap headers;
    std::size_t pos = first_line_end + 2;
    while (pos < block.size()) {
        std::size_t end = block.find("\r\n", pos);
        if (end == std::string::npos || end == pos) {
            break;
        }
        std::string_view line(block.data() + pos, end - pos);
        std::size_t colon = line.find(':');
        if (colon != std::string_view::npos) {
            std::string name = trim(line.substr(0, colon));
            std::string value = trim(line.substr(colon + 1));
            if (!name.empty()) {
                headers[lower(name)] = value;
            }
        }
        pos = end + 2;
    }
    return headers;
}

std::vector<std::uint8_t> read_body_remainder(int fd,
                                              std::vector<std::uint8_t> raw,
                                              std::size_t header_len,
                                              std::size_t content_length,
                                              std::size_t max_body) {
    if (content_length > max_body) {
        throw std::runtime_error("body too large");
    }
    std::array<char, 8192> chunk{};
    while (raw.size() < header_len + content_length) {
        ssize_t n = read(fd, chunk.data(), chunk.size());
        if (n == 0) {
            throw std::runtime_error("connection closed while reading body");
        }
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            throw std::runtime_error("read failed while reading body");
        }
        raw.insert(raw.end(), chunk.data(), chunk.data() + n);
    }
    return std::vector<std::uint8_t>(raw.begin() + static_cast<long>(header_len),
                                    raw.begin() + static_cast<long>(header_len + content_length));
}

class BodyReader {
public:
    BodyReader(int fd, std::vector<std::uint8_t> buffered) : fd_(fd), buffered_(std::move(buffered)) {}

    std::uint8_t read_byte() {
        ensure(1);
        return buffered_[offset_++];
    }

    std::vector<std::uint8_t> read_exact(std::size_t n) {
        ensure(n);
        std::vector<std::uint8_t> out(buffered_.begin() + static_cast<long>(offset_),
                                      buffered_.begin() + static_cast<long>(offset_ + n));
        offset_ += n;
        return out;
    }

    std::string read_line(std::size_t max_line = 8192) {
        std::string out;
        out.reserve(64);
        for (;;) {
            if (out.size() > max_line) {
                throw std::runtime_error("chunk control line too large");
            }
            char c = static_cast<char>(read_byte());
            out.push_back(c);
            if (out.size() >= 2 && out[out.size() - 2] == '\r' && out[out.size() - 1] == '\n') {
                out.resize(out.size() - 2);
                return out;
            }
        }
    }

private:
    void ensure(std::size_t n) {
        std::array<std::uint8_t, 8192> chunk{};
        while (buffered_.size() - offset_ < n) {
            ssize_t got = read(fd_, chunk.data(), chunk.size());
            if (got == 0) {
                throw std::runtime_error("connection closed while reading transfer body");
            }
            if (got < 0) {
                if (errno == EINTR) {
                    continue;
                }
                throw std::runtime_error("read failed while reading transfer body");
            }
            buffered_.insert(buffered_.end(), chunk.data(), chunk.data() + got);
        }
    }

    int fd_;
    std::vector<std::uint8_t> buffered_;
    std::size_t offset_ = 0;
};

std::size_t parse_chunk_size(const std::string& line) {
    std::string_view view(line);
    std::size_t semicolon = view.find(';');
    if (semicolon != std::string_view::npos) {
        view = view.substr(0, semicolon);
    }
    std::string token = trim(view);
    std::size_t size = 0;
    auto begin = token.data();
    auto end = token.data() + token.size();
    auto result = std::from_chars(begin, end, size, 16);
    if (token.empty() || result.ec != std::errc{} || result.ptr != end) {
        throw std::runtime_error("invalid chunk size");
    }
    return size;
}

void read_chunked_response_body(int fd,
                                const std::vector<std::uint8_t>& buffered,
                                const ReadLimits& limits,
                                HttpResponse& response) {
    BodyReader reader(fd, buffered);
    std::size_t total = 0;
    for (;;) {
        std::size_t size = parse_chunk_size(reader.read_line());
        if (size == 0) {
            for (;;) {
                if (reader.read_line().empty()) {
                    break;
                }
            }
            break;
        }
        if (total + size > limits.max_body_bytes) {
            throw std::runtime_error("chunked response body too large");
        }
        auto data = reader.read_exact(size);
        auto crlf = reader.read_exact(2);
        if (crlf.size() != 2 || crlf[0] != '\r' || crlf[1] != '\n') {
            throw std::runtime_error("malformed chunk delimiter");
        }
        total += size;
        response.body.insert(response.body.end(), data.begin(), data.end());
        response.transfer_chunks.push_back(std::move(data));
    }
    response.chunked = true;
}

void append_ascii(std::vector<std::uint8_t>& out, const std::string& text) {
    out.insert(out.end(), text.begin(), text.end());
}

std::string reason_for(int status) {
    switch (status) {
        case 200:
            return "OK";
        case 201:
            return "Created";
        case 400:
            return "Bad Request";
        case 413:
            return "Payload Too Large";
        case 415:
            return "Unsupported Media Type";
        case 502:
            return "Bad Gateway";
        case 504:
            return "Gateway Timeout";
        default:
            return "Error";
    }
}

}  // namespace

std::optional<std::string> header_value(const HeaderMap& headers, std::string_view name) {
    auto it = headers.find(lower(name));
    if (it == headers.end()) {
        return std::nullopt;
    }
    return it->second;
}

void set_header(HeaderMap& headers, const std::string& name, const std::string& value) {
    headers[lower(name)] = value;
}

void erase_header(HeaderMap& headers, std::string_view name) {
    headers.erase(lower(name));
}

bool has_token_header(const HeaderMap& headers, std::string_view name, std::string_view token) {
    auto value = header_value(headers, name);
    if (!value) {
        return false;
    }
    std::string haystack = lower(*value);
    std::string needle = lower(token);
    std::size_t pos = 0;
    while (pos <= haystack.size()) {
        std::size_t comma = haystack.find(',', pos);
        std::string part = trim(std::string_view(haystack).substr(pos, comma == std::string::npos ? std::string::npos : comma - pos));
        if (part == needle) {
            return true;
        }
        if (comma == std::string::npos) {
            break;
        }
        pos = comma + 1;
    }
    return false;
}

HttpRequest read_http_request(int fd, const ReadLimits& limits) {
    std::size_t header_len = 0;
    auto raw = read_http_message_bytes(fd, limits, header_len);
    std::string header_block(reinterpret_cast<const char*>(raw.data()), header_len);
    std::size_t first_end = header_block.find("\r\n");
    if (first_end == std::string::npos) {
        throw std::runtime_error("malformed request line");
    }

    std::istringstream line(header_block.substr(0, first_end));
    HttpRequest request;
    if (!(line >> request.method >> request.target >> request.version)) {
        throw std::runtime_error("malformed request line");
    }
    request.headers = parse_headers(header_block, first_end);
    if (has_token_header(request.headers, "Transfer-Encoding", "chunked")) {
        throw std::runtime_error("chunked request bodies are not accepted");
    }
    std::size_t content_length = parse_content_length(request.headers);
    request.body = read_body_remainder(fd, std::move(raw), header_len, content_length, limits.max_body_bytes);
    return request;
}

HttpResponse read_http_response(int fd, const ReadLimits& limits) {
    std::size_t header_len = 0;
    auto raw = read_http_message_bytes(fd, limits, header_len);
    std::string header_block(reinterpret_cast<const char*>(raw.data()), header_len);
    std::size_t first_end = header_block.find("\r\n");
    if (first_end == std::string::npos) {
        throw std::runtime_error("malformed response line");
    }

    std::istringstream line(header_block.substr(0, first_end));
    HttpResponse response;
    if (!(line >> response.version >> response.status)) {
        throw std::runtime_error("malformed response line");
    }
    std::getline(line, response.reason);
    response.reason = trim(response.reason);
    if (response.reason.empty()) {
        response.reason = reason_for(response.status);
    }
    response.headers = parse_headers(header_block, first_end);

    if (has_token_header(response.headers, "Transfer-Encoding", "chunked")) {
        std::vector<std::uint8_t> buffered(raw.begin() + static_cast<long>(header_len), raw.end());
        read_chunked_response_body(fd, buffered, limits, response);
        return response;
    }

    std::size_t content_length = parse_content_length(response.headers);
    response.body = read_body_remainder(fd, std::move(raw), header_len, content_length, limits.max_body_bytes);
    return response;
}

std::vector<std::uint8_t> serialize_request(const HttpRequest& request) {
    std::vector<std::uint8_t> out;
    out.reserve(request.body.size() + 4096);
    append_ascii(out, request.method + " " + request.target + " HTTP/1.1\r\n");
    for (const auto& [name, value] : request.headers) {
        append_ascii(out, name + ": " + value + "\r\n");
    }
    append_ascii(out, "\r\n");
    out.insert(out.end(), request.body.begin(), request.body.end());
    return out;
}

std::vector<std::uint8_t> serialize_response(const HttpResponse& response) {
    std::vector<std::uint8_t> out;
    out.reserve(response.body.size() + 4096);
    append_ascii(out, "HTTP/1.1 " + std::to_string(response.status) + " " + response.reason + "\r\n");
    for (const auto& [name, value] : response.headers) {
        append_ascii(out, name + ": " + value + "\r\n");
    }
    append_ascii(out, "\r\n");
    out.insert(out.end(), response.body.begin(), response.body.end());
    return out;
}

HttpResponse text_response(int status, const std::string& reason, const std::string& body) {
    HttpResponse response;
    response.status = status;
    response.reason = reason;
    response.body.assign(body.begin(), body.end());
    set_header(response.headers, "Content-Type", "text/plain; charset=utf-8");
    set_header(response.headers, "Content-Length", std::to_string(response.body.size()));
    set_header(response.headers, "Connection", "close");
    return response;
}

std::string origin_form_target(const std::string& target) {
    if (target.rfind("http://", 0) == 0) {
        auto slash = target.find('/', 7);
        return slash == std::string::npos ? "/" : target.substr(slash);
    }
    if (target.rfind("https://", 0) == 0) {
        auto slash = target.find('/', 8);
        return slash == std::string::npos ? "/" : target.substr(slash);
    }
    return target.empty() ? "/" : target;
}

bool cacheable_response(const HttpRequest& request, const HttpResponse& response, std::size_t max_object) {
    if (request.method != "GET" || response.status != 200 || response.body.size() > max_object) {
        return false;
    }
    if (has_token_header(response.headers, "Cache-Control", "no-store")) {
        return false;
    }
    auto type = header_value(response.headers, "Content-Type");
    if (!type) {
        return false;
    }
    return type->find("text/") != std::string::npos ||
           type->find("application/json") != std::string::npos ||
           type->find("application/javascript") != std::string::npos;
}

}  // namespace p1groxy
