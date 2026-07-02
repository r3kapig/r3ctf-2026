#include "seal/seal.h"

#include <cstdlib>
#include <cmath>
#include <complex>
#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace seal;

void setup(std::unique_ptr<SEALContext>& context,
           std::unique_ptr<CKKSEncoder>& encoder,
           std::unique_ptr<Encryptor>& encryptor,
           std::unique_ptr<Decryptor>& decryptor,
           std::unique_ptr<SecretKey>& secret_key,
           std::unique_ptr<PublicKey>& public_key,
           uint64_t& q,
           uint64_t& delta) {
    EncryptionParameters parms(scheme_type::ckks);
    parms.set_poly_modulus_degree(4096);
    parms.set_coeff_modulus(CoeffModulus::Create(4096, {60}));

    context = std::make_unique<SEALContext>(parms, true, sec_level_type::none);
    encoder = std::make_unique<CKKSEncoder>(*context);

    q = context->first_context_data()->parms().coeff_modulus()[0].value();

    std::random_device rd;
    std::mt19937_64 rng((static_cast<uint64_t>(rd()) << 32) ^ rd());
    std::uniform_int_distribution<uint64_t> dist(1, q - 1);
    delta = dist(rng);

    KeyGenerator keygen(*context);
    secret_key = std::make_unique<SecretKey>(keygen.secret_key());
    public_key = std::make_unique<PublicKey>();
    keygen.create_public_key(*public_key);

    encryptor = std::make_unique<Encryptor>(*context, *public_key);
    decryptor = std::make_unique<Decryptor>(*context, *secret_key);
}

std::string encrypt(CKKSEncoder& encoder, Encryptor& encryptor, uint64_t q, uint64_t delta, const std::vector<std::complex<double>>& values) {
    if (values.size() != encoder.slot_count()) {
        throw std::invalid_argument("vector length must be N/2");
    }

    Plaintext check_plain;
    encoder.encode_chall(values, 1, check_plain);

    std::vector<uint64_t> plain_coeffs;
    encoder.export_chall_coefficients(check_plain, plain_coeffs);
    for (uint64_t coeff : plain_coeffs) {
        uint64_t abs_coeff = coeff > q / 2 ? q - coeff : coeff;
        if (abs_coeff < q / 8) {
            throw std::invalid_argument("bad plaintext");
        }
    }

    Plaintext plain;
    encoder.encode_chall(values, delta, plain);

    Ciphertext ct;
    encryptor.encrypt(plain, ct);

    std::stringstream raw(std::ios::in | std::ios::out | std::ios::binary);
    ct.save(raw, compr_mode_type::none);
    return raw.str();
}

std::vector<uint64_t> decrypt(SEALContext& context, CKKSEncoder& encoder, Decryptor& decryptor, const std::string& raw) {
    std::stringstream in(std::ios::in | std::ios::out | std::ios::binary);
    in.write(raw.data(), static_cast<std::streamsize>(raw.size()));
    in.seekg(0);

    Ciphertext ct;
    ct.load(context, in);

    Plaintext plain;
    decryptor.decrypt(ct, plain);

    std::vector<uint64_t> coeffs;
    encoder.export_chall_coefficients(plain, coeffs);
    return coeffs;
}

int main() {
    try {
        std::unique_ptr<SEALContext> context;
        std::unique_ptr<CKKSEncoder> encoder;
        std::unique_ptr<Encryptor> encryptor;
        std::unique_ptr<Decryptor> decryptor;
        std::unique_ptr<SecretKey> secret_key;
        std::unique_ptr<PublicKey> public_key;
        uint64_t q = 0;
        uint64_t delta = 0;

        setup(context, encoder, encryptor, decryptor, secret_key, public_key, q, delta);

        std::random_device noise_rd;
        std::mt19937_64 noise_rng((static_cast<uint64_t>(noise_rd()) << 32) ^ noise_rd());
        std::uniform_int_distribution<uint64_t> noise_dist(0, (1ULL << 57) - 1);

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

                    std::string ct = encrypt(*encoder, *encryptor, q, delta, values);
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
                        if (i < 126) {
                            uint64_t noise = noise_dist(noise_rng);
                            uint64_t value = 0;
                            if (noise_rng() & 1) {
                                value = (coeffs[i] + noise) % q;
                            } else {
                                value = (coeffs[i] + q - noise) % q;
                            }
                            std::cout << value;
                        } else {
                            std::cout << '*';
                        }
                    }
                    std::cout << '\n';
                } else if (choice == 3) {
                    uint64_t guess = 0;
                    std::cout << "delta> " << std::flush;
                    std::cin >> guess;

                    if (std::cin && guess % q == delta) {
                        const char *flag = std::getenv("FLAG");
                        if (!flag || !*flag) {
                            std::cout << "FLAG environment variable not set\n";
                        } else {
                            std::cout << flag << '\n';
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
