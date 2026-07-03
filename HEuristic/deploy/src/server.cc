#include "seal/seal.h"

#include <cmath>
#include <complex>
#include <csignal>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <boost/multiprecision/cpp_int.hpp>
#include <unistd.h>

using namespace seal;
using boost::multiprecision::cpp_int;

void timeout_handler(int) {
    _exit(0);
}

cpp_int from_limbs(const std::vector<uint64_t>& limbs) {
    cpp_int value = 0;
    for (auto it = limbs.rbegin(); it != limbs.rend(); ++it) {
        value <<= 64;
        value += *it;
    }
    return value;
}

std::vector<uint64_t> to_rns(const cpp_int& value, const std::vector<Modulus>& moduli) {
    std::vector<uint64_t> result;
    result.reserve(moduli.size());
    for (const auto& modulus : moduli) {
        cpp_int reduced = value % modulus.value();
        if (reduced < 0) {
            reduced += modulus.value();
        }
        result.push_back(reduced.convert_to<uint64_t>());
    }
    return result;
}

cpp_int random_below(const cpp_int& upper, std::mt19937_64& rng) {
    if (upper <= 0) {
        return 0;
    }

    size_t bits = boost::multiprecision::msb(upper) + 1;
    size_t limbs = (bits + 63) / 64;
    size_t high_bits = bits % 64;
    uint64_t high_mask = high_bits ? ((uint64_t(1) << high_bits) - 1) : ~uint64_t(0);

    for (;;) {
        cpp_int value = 0;
        for (size_t i = 0; i < limbs; ++i) {
            uint64_t limb = rng();
            if (i + 1 == limbs) {
                limb &= high_mask;
            }
            value += cpp_int(limb) << (64 * i);
        }
        if (value < upper) {
            return value;
        }
    }
}

cpp_int parse_cpp_int(const std::string& s) {
    cpp_int value = 0;
    std::stringstream in(s);
    in >> value;
    if (!in || !in.eof()) {
        throw std::invalid_argument("bad integer");
    }
    return value;
}

void setup(std::unique_ptr<SEALContext>& context,
           std::unique_ptr<CKKSEncoder>& encoder,
           std::unique_ptr<Encryptor>& encryptor,
           std::unique_ptr<Decryptor>& decryptor,
           std::unique_ptr<SecretKey>& secret_key,
           std::unique_ptr<PublicKey>& public_key,
           cpp_int& q,
           cpp_int& delta) {
    EncryptionParameters parms(scheme_type::ckks);
    parms.set_poly_modulus_degree(4096);
    parms.set_coeff_modulus(CoeffModulus::Create(4096, {48, 48, 48, 48, 48}));

    context = std::make_unique<SEALContext>(parms, true, sec_level_type::none);
    encoder = std::make_unique<CKKSEncoder>(*context);

    q = 1;
    for (const auto& modulus : context->first_context_data()->parms().coeff_modulus()) {
        q *= modulus.value();
    }

    std::random_device rd;
    std::mt19937_64 rng((static_cast<uint64_t>(rd()) << 32) ^ rd());
    delta = random_below(q - 1, rng) + 1;

    KeyGenerator keygen(*context);
    secret_key = std::make_unique<SecretKey>(keygen.secret_key());
    public_key = std::make_unique<PublicKey>();
    keygen.create_public_key(*public_key);

    encryptor = std::make_unique<Encryptor>(*context, *public_key);
    decryptor = std::make_unique<Decryptor>(*context, *secret_key);
}

std::string encrypt(CKKSEncoder& encoder, Encryptor& encryptor, const std::vector<Modulus>& moduli, const cpp_int& q, const cpp_int& delta, const std::vector<std::complex<double>>& values) {
    if (values.size() != encoder.slot_count()) {
        throw std::invalid_argument("vector length must be N/2");
    }

    Plaintext check_plain;
    encoder.encode_chall(values, 1, check_plain);

    std::vector<std::vector<uint64_t>> plain_coeffs;
    encoder.export_chall_coefficients(check_plain, plain_coeffs);
    for (const auto& coeff_limbs : plain_coeffs) {
        cpp_int coeff = from_limbs(coeff_limbs);
        cpp_int abs_coeff = coeff > q / 2 ? q - coeff : coeff;
        if (abs_coeff < q / 8) {
            throw std::invalid_argument("bad plaintext");
        }
    }

    Plaintext plain;
    encoder.encode_chall(values, to_rns(delta, moduli), plain);

    Ciphertext ct;
    encryptor.encrypt(plain, ct);

    std::stringstream raw(std::ios::in | std::ios::out | std::ios::binary);
    ct.save(raw, compr_mode_type::none);
    return raw.str();
}

std::vector<cpp_int> decrypt(SEALContext& context, CKKSEncoder& encoder, Decryptor& decryptor, const std::string& raw) {
    std::stringstream in(std::ios::in | std::ios::out | std::ios::binary);
    in.write(raw.data(), static_cast<std::streamsize>(raw.size()));
    in.seekg(0);

    Ciphertext ct;
    ct.load(context, in);

    Plaintext plain;
    decryptor.decrypt(ct, plain);

    std::vector<std::vector<uint64_t>> coeff_limbs;
    encoder.export_chall_coefficients(plain, coeff_limbs);

    std::vector<cpp_int> coeffs;
    coeffs.reserve(coeff_limbs.size());
    for (const auto& limbs : coeff_limbs) {
        coeffs.push_back(from_limbs(limbs));
    }
    return coeffs;
}

int main() {
    try {
        std::signal(SIGALRM, timeout_handler);
        alarm(300);

        std::unique_ptr<SEALContext> context;
        std::unique_ptr<CKKSEncoder> encoder;
        std::unique_ptr<Encryptor> encryptor;
        std::unique_ptr<Decryptor> decryptor;
        std::unique_ptr<SecretKey> secret_key;
        std::unique_ptr<PublicKey> public_key;
        cpp_int q = 0;
        cpp_int delta = 0;

        setup(context, encoder, encryptor, decryptor, secret_key, public_key, q, delta);
        const auto& moduli = context->first_context_data()->parms().coeff_modulus();

        std::random_device noise_rd;
        std::mt19937_64 noise_rng((static_cast<uint64_t>(noise_rd()) << 32) ^ noise_rd());
        cpp_int noise_bound = cpp_int(1) << 169;

        std::cout << "q = " << q << '\n';

        for (int round = 0; round < 3; ++round) {
            std::cout << "\n1. encrypt\n2. decrypt\n3. submit\n4. exit\n> " << std::flush;

            int choice = 0;
            if (!(std::cin >> choice)) {
                return 0;
            }

            try {
                if (choice == 1) {
                    size_t n = 0;
                    std::cout << "input n followed by n lines of: real imag\n";
                    std::cin >> n;
                    if (!std::cin || n != encoder->slot_count()) {
                        throw std::invalid_argument("bad vector length");
                    }

                    std::vector<std::complex<double>> values;
                    values.reserve(n);
                    for (size_t i = 0; i < n; ++i) {
                        double real = 0;
                        double imag = 0;
                        std::cin >> real >> imag;
                        if (!std::cin || !std::isfinite(real) || !std::isfinite(imag)) {
                            throw std::invalid_argument("bad vector entry");
                        }
                        values.emplace_back(real, imag);
                    }

                    std::string ct = encrypt(*encoder, *encryptor, moduli, q, delta, values);
                    std::cout << "ciphertext length: " << ct.size() << '\n';
                    std::cout.write(ct.data(), static_cast<std::streamsize>(ct.size()));
                    std::cout << '\n';
                } else if (choice == 2) {
                    size_t ct_len = 0;
                    std::cout << "ciphertext length> " << std::flush;
                    std::cin >> ct_len;
                    if (!std::cin) {
                        throw std::invalid_argument("bad ciphertext length");
                    }
                    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');

                    std::string ct(ct_len, '\0');
                    std::cin.read(ct.data(), static_cast<std::streamsize>(ct.size()));
                    if (static_cast<size_t>(std::cin.gcount()) != ct.size()) {
                        throw std::invalid_argument("truncated ciphertext");
                    }

                    auto coeffs = decrypt(*context, *encoder, *decryptor, ct);
                    for (size_t i = 0; i < coeffs.size(); ++i) {
                        if (i) {
                            std::cout << ' ';
                        }
                        if (i < 96) {
                            cpp_int noise = random_below(noise_bound, noise_rng);
                            cpp_int value = 0;
                            if (noise_rng() & 1) {
                                value = (coeffs[i] + noise) % q;
                            } else {
                                value = (coeffs[i] - noise) % q;
                                if (value < 0) {
                                    value += q;
                                }
                            }
                            std::cout << value;
                        } else {
                            std::cout << '*';
                        }
                    }
                    std::cout << '\n';
                } else if (choice == 3) {
                    std::string guess_text;
                    std::cout << "delta> " << std::flush;
                    std::cin >> guess_text;

                    cpp_int guess = parse_cpp_int(guess_text);
                    guess %= q;
                    if (guess < 0) {
                        guess += q;
                    }

                    if (std::cin && guess == delta) {
                        std::ifstream flag("flag");
                        if (!flag) {
                            std::cout << "flag file not found\n";
                        } else {
                            std::string content;
                            std::getline(flag, content);
                            std::cout << content << '\n';
                        }
                        return 0;
                    } else {
                        std::cout << "wrong\n";
                    }
                } else if (choice == 4) {
                    std::cout << "bye\n";
                    return 0;
                } else {
                    std::cout << "invalid choice\n";
                }
            } catch (const std::exception& e) {
                std::cout << "error: " << e.what() << '\n';
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "fatal: " << e.what() << '\n';
        return 1;
    }
}
