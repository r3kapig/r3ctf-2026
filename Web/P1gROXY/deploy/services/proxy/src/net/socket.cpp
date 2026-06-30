#include "p1groxy/socket.hpp"

#include <cerrno>
#include <cstdint>
#include <cstring>
#include <stdexcept>

#include <fcntl.h>
#include <netdb.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

namespace p1groxy {

UniqueFd::~UniqueFd() {
    reset();
}

UniqueFd::UniqueFd(UniqueFd&& other) noexcept : fd_(other.release()) {}

UniqueFd& UniqueFd::operator=(UniqueFd&& other) noexcept {
    if (this != &other) {
        reset(other.release());
    }
    return *this;
}

int UniqueFd::release() {
    int fd = fd_;
    fd_ = -1;
    return fd;
}

void UniqueFd::reset(int fd) {
    if (fd_ >= 0) {
        close(fd_);
    }
    fd_ = fd;
}

void set_socket_timeout(int fd, int seconds) {
    timeval tv{};
    tv.tv_sec = seconds;
    tv.tv_usec = 0;
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
}

UniqueFd listen_tcp(const std::string& host, const std::string& port, int backlog) {
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;

    addrinfo* result = nullptr;
    int rc = getaddrinfo(host.c_str(), port.c_str(), &hints, &result);
    if (rc != 0) {
        throw std::runtime_error(std::string("getaddrinfo: ") + gai_strerror(rc));
    }

    UniqueFd listener;
    for (addrinfo* rp = result; rp; rp = rp->ai_next) {
        UniqueFd fd(socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol));
        if (!fd.valid()) {
            continue;
        }
        int one = 1;
        setsockopt(fd.get(), SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
        if (bind(fd.get(), rp->ai_addr, rp->ai_addrlen) == 0 && listen(fd.get(), backlog) == 0) {
            listener = std::move(fd);
            break;
        }
    }
    freeaddrinfo(result);

    if (!listener.valid()) {
        throw std::runtime_error("could not bind " + host + ":" + port);
    }
    return listener;
}

UniqueFd connect_tcp(const std::string& host, const std::string& port, int timeout_seconds) {
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo* result = nullptr;
    int rc = getaddrinfo(host.c_str(), port.c_str(), &hints, &result);
    if (rc != 0) {
        throw std::runtime_error(std::string("getaddrinfo upstream: ") + gai_strerror(rc));
    }

    UniqueFd connected;
    for (addrinfo* rp = result; rp; rp = rp->ai_next) {
        UniqueFd fd(socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol));
        if (!fd.valid()) {
            continue;
        }
        set_socket_timeout(fd.get(), timeout_seconds);
        if (connect(fd.get(), rp->ai_addr, rp->ai_addrlen) == 0) {
            connected = std::move(fd);
            break;
        }
    }
    freeaddrinfo(result);

    if (!connected.valid()) {
        throw std::runtime_error("could not connect upstream " + host + ":" + port);
    }
    return connected;
}

void write_all(int fd, const void* data, std::size_t len) {
    const auto* p = static_cast<const std::uint8_t*>(data);
    while (len > 0) {
        ssize_t n = write(fd, p, len);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            throw std::runtime_error(std::string("write: ") + std::strerror(errno));
        }
        if (n == 0) {
            throw std::runtime_error("write returned zero");
        }
        p += n;
        len -= static_cast<std::size_t>(n);
    }
}

void write_all(int fd, const std::vector<std::uint8_t>& data) {
    write_all(fd, data.data(), data.size());
}

}  // namespace p1groxy
