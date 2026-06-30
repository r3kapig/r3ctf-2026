#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace p1groxy {

class ContentCoding {
public:
    std::vector<std::uint8_t> decode(const std::string& encoding,
                                     const std::vector<std::uint8_t>& input);
    std::vector<std::uint8_t> decode_transfer_fragment(const std::string& encoding,
                                                       const std::vector<std::uint8_t>& input);

private:
    std::vector<std::uint8_t> inflate_wrapped(int window_bits,
                                             const std::vector<std::uint8_t>& input);
    std::vector<std::uint8_t> inflate_raw_streaming(const std::vector<std::uint8_t>& input);
    std::vector<std::uint8_t> inflate_raw_streaming_lenient(const std::vector<std::uint8_t>& input);
    std::vector<std::uint8_t> workspace_;
};

}  // namespace p1groxy
