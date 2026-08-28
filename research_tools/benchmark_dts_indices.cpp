// Capability benchmark for a difference-indexed bitset compatibility representation.

#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Header {
    std::uint32_t magic;
    std::uint32_t version;
    std::uint32_t scope_limit;
    std::uint32_t record_size;
    std::uint64_t count;
};

struct Row {
    std::uint8_t marks[6];
    std::uint8_t scope;
    std::uint8_t reserved[1];
    std::uint64_t lo;
    std::uint64_t hi;
};

static std::vector<Row> read_catalogue(const std::string& path, Header& header) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open catalogue");
    input.read(reinterpret_cast<char*>(&header), sizeof(header));
    if (!input || header.magic != 0x44545352 || header.version != 1 || header.record_size != sizeof(Row)) throw std::runtime_error("invalid catalogue header");
    std::vector<Row> rows(static_cast<std::size_t>(header.count));
    input.read(reinterpret_cast<char*>(rows.data()), static_cast<std::streamsize>(rows.size() * sizeof(Row)));
    if (!input) throw std::runtime_error("short catalogue");
    return rows;
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: benchmark_dts_indices CATALOGUE");
        Header header{};
        const auto rows = read_catalogue(argv[1], header);
        const std::size_t words = (rows.size() + 63) / 64;
        const auto started = std::chrono::steady_clock::now();
        std::vector<std::uint64_t> incidence(111 * words, 0);
        std::uint64_t set_bits = 0;
        for (std::size_t index = 0; index < rows.size(); ++index) {
            for (int difference = 1; difference <= 111; ++difference) {
                const bool present = difference <= 64
                    ? (rows[index].lo & (std::uint64_t(1) << (difference - 1))) != 0
                    : (rows[index].hi & (std::uint64_t(1) << (difference - 65))) != 0;
                if (!present) continue;
                incidence[static_cast<std::size_t>(difference - 1) * words + index / 64] |= std::uint64_t(1) << (index % 64);
                ++set_bits;
            }
        }
        const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
        std::cout << std::setprecision(12)
                  << "{\"rows\":" << rows.size()
                  << ",\"difference_columns\":111"
                  << ",\"words_per_column\":" << words
                  << ",\"set_bits\":" << set_bits
                  << ",\"expected_set_bits\":" << (rows.size() * 15)
                  << ",\"index_bytes\":" << (incidence.size() * sizeof(std::uint64_t))
                  << ",\"build_seconds\":" << seconds
                  << ",\"rows_per_second\":" << (rows.size() / seconds)
                  << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
