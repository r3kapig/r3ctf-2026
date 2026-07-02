#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace p1groxy {

class UniqueFd {
public:
    UniqueFd() = default;
    explicit UniqueFd(int fd) : fd_(fd) {}
    ~UniqueFd();

    UniqueFd(const UniqueFd&) = delete;
    UniqueFd& operator=(const UniqueFd&) = delete;

    UniqueFd(UniqueFd&& other) noexcept;
    UniqueFd& operator=(UniqueFd&& other) noexcept;

    int get() const { return fd_; }
    int release();
    bool valid() const { return fd_ >= 0; }
    void reset(int fd = -1);

private:
    int fd_ = -1;
};

UniqueFd listen_tcp(const std::string& host, const std::string& port, int backlog);
UniqueFd connect_tcp(const std::string& host, const std::string& port, int timeout_seconds);
void set_socket_timeout(int fd, int seconds);
void write_all(int fd, const std::vector<std::uint8_t>& data);
void write_all(int fd, const void* data, std::size_t len);

}  // namespace p1groxy
