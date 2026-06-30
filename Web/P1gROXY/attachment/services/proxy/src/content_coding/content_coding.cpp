#include "p1groxy/content_coding.hpp"

#include "zlib.h"

#include <array>
#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <strings.h>

namespace p1groxy {
namespace {

constexpr unsigned kWindowBits = 15;
constexpr std::size_t kWindowSize = 1u << kWindowBits;
constexpr std::size_t kChunkSize = 16 * 1024;

struct BackInput {
    const std::vector<std::uint8_t>* input = nullptr;
    std::size_t offset = 0;
    std::size_t prelude_remaining = 0;
    std::size_t prelude_quantum = 4;
    std::size_t bulk_size = kChunkSize;
};

struct BackOutput {
    std::vector<std::uint8_t>* output = nullptr;
};

unsigned back_input(void* opaque, unsigned char** buf) {
    auto* in = static_cast<BackInput*>(opaque);
    if (in->offset >= in->input->size()) {
        *buf = Z_NULL;
        return 0;
    }
    std::size_t remaining = in->input->size() - in->offset;
    std::size_t target = in->bulk_size;
    if (in->prelude_remaining > 0) {
        target = std::min(in->prelude_quantum, in->prelude_remaining);
        in->prelude_remaining -= target;
    }
    std::size_t n = std::min(remaining, target);
    *buf = const_cast<unsigned char*>(in->input->data() + in->offset);
    in->offset += n;
    return static_cast<unsigned>(n);
}

int back_output(void* opaque, unsigned char* buf, unsigned len) {
    auto* out = static_cast<BackOutput*>(opaque);
    out->output->insert(out->output->end(), buf, buf + len);
    return 0;
}

bool equals_ignore_case(const std::string& lhs, const char* rhs) {
    return strcasecmp(lhs.c_str(), rhs) == 0;
}

}  // namespace

std::vector<std::uint8_t> ContentCoding::decode(const std::string& encoding,
                                                const std::vector<std::uint8_t>& input) {
    if (encoding.empty() || equals_ignore_case(encoding, "identity")) {
        return input;
    }
    if (equals_ignore_case(encoding, "gzip")) {
        return inflate_wrapped(16 + MAX_WBITS, input);
    }
    if (equals_ignore_case(encoding, "deflate")) {
        try {
            return inflate_wrapped(MAX_WBITS, input);
        } catch (const std::exception&) {
            return inflate_raw_streaming(input);
        }
    }
    throw std::runtime_error("unsupported content coding: " + encoding);
}

std::vector<std::uint8_t> ContentCoding::decode_transfer_fragment(const std::string& encoding,
                                                                  const std::vector<std::uint8_t>& input) {
    if (encoding.empty() || equals_ignore_case(encoding, "identity")) {
        return input;
    }
    if (equals_ignore_case(encoding, "gzip")) {
        return inflate_wrapped(16 + MAX_WBITS, input);
    }
    if (equals_ignore_case(encoding, "deflate")) {
        try {
            return inflate_wrapped(MAX_WBITS, input);
        } catch (const std::exception&) {
            return inflate_raw_streaming_lenient(input);
        }
    }
    throw std::runtime_error("unsupported content coding fragment: " + encoding);
}

std::vector<std::uint8_t> ContentCoding::inflate_wrapped(int window_bits,
                                                         const std::vector<std::uint8_t>& input) {
    z_stream stream{};
    if (inflateInit2(&stream, window_bits) != Z_OK) {
        throw std::runtime_error("inflateInit2 failed");
    }

    std::vector<std::uint8_t> output;
    std::array<std::uint8_t, kChunkSize> chunk{};
    stream.next_in = const_cast<Bytef*>(input.data());
    stream.avail_in = static_cast<uInt>(input.size());

    int rc = Z_OK;
    while (rc != Z_STREAM_END) {
        stream.next_out = chunk.data();
        stream.avail_out = chunk.size();
        rc = inflate(&stream, Z_NO_FLUSH);
        if (rc != Z_OK && rc != Z_STREAM_END) {
            inflateEnd(&stream);
            throw std::runtime_error("inflate failed");
        }
        std::size_t have = chunk.size() - stream.avail_out;
        output.insert(output.end(), chunk.data(), chunk.data() + have);
        if (output.size() > 64 * 1024 * 1024) {
            inflateEnd(&stream);
            throw std::runtime_error("decoded body too large");
        }
    }

    inflateEnd(&stream);
    return output;
}

std::vector<std::uint8_t> ContentCoding::inflate_raw_streaming_lenient(const std::vector<std::uint8_t>& input) {
    if (workspace_.empty()) {
        workspace_.resize(kWindowSize);
    }

    z_stream stream{};
    int rc = inflateBackInit(&stream, static_cast<int>(kWindowBits), workspace_.data());
    if (rc != Z_OK) {
        throw std::runtime_error("raw deflate fragment adapter init failed");
    }

    std::vector<std::uint8_t> output;
    BackInput in{&input, 0, 64, 4, kChunkSize};
    BackOutput out{&output};
    rc = inflateBack(&stream, back_input, &in, back_output, &out);
    inflateBackEnd(&stream);
    (void)rc;
    return output;
}

std::vector<std::uint8_t> ContentCoding::inflate_raw_streaming(const std::vector<std::uint8_t>& input) {
    if (workspace_.empty()) {
        workspace_.resize(kWindowSize);
    }

    z_stream stream{};
    int rc = inflateBackInit(&stream, static_cast<int>(kWindowBits), workspace_.data());
    if (rc != Z_OK) {
        throw std::runtime_error("raw deflate adapter init failed");
    }

    std::vector<std::uint8_t> output;
    BackInput in{&input, 0, 0, 4, kChunkSize};
    BackOutput out{&output};
    rc = inflateBack(&stream, back_input, &in, back_output, &out);
    inflateBackEnd(&stream);
    if (rc != Z_STREAM_END) {
        throw std::runtime_error("raw deflate adapter failed");
    }
    return output;
}

}  // namespace p1groxy
