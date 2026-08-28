// Exhaustive normalized six-mark Golomb-ruler enumeration for DTS capability audits.
// Differences are represented exactly by two 64-bit words for 1..111.

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Mask {
    std::uint64_t lo = 0;
    std::uint64_t hi = 0;

    bool contains(int difference) const {
        if (difference <= 64) return (lo & (std::uint64_t(1) << (difference - 1))) != 0;
        return (hi & (std::uint64_t(1) << (difference - 65))) != 0;
    }

    void add(int difference) {
        if (difference <= 64) lo |= std::uint64_t(1) << (difference - 1);
        else hi |= std::uint64_t(1) << (difference - 65);
    }
};

struct PackedRow {
    std::uint8_t marks[6];
    std::uint8_t scope;
    std::uint8_t reserved[1];
    std::uint64_t lo;
    std::uint64_t hi;
};

struct Counts {
    std::uint64_t raw_complete_choices = 0;
    std::uint64_t valid_rows = 0;
    std::uint64_t prefixes_considered[5] = {};
    std::uint64_t prefixes_pruned[5] = {};
    std::uint64_t by_scope[112] = {};
    std::uint64_t reflection_representatives = 0;
};

static std::uint64_t choose5(int scope) {
    std::uint64_t result = 1;
    for (int i = 1; i <= 5; ++i) result = result * static_cast<std::uint64_t>(scope - 5 + i) / static_cast<std::uint64_t>(i);
    return result;
}

class Enumerator {
public:
    explicit Enumerator(int scope_limit, bool store_rows, std::size_t reserve_rows) : scope_limit_(scope_limit), store_rows_(store_rows) {
        if (store_rows_ && reserve_rows > 0) rows_.reserve(reserve_rows);
    }

    void run() {
        row_[0] = 0;
        recurse(1, 1, Mask{});
    }

    const Counts& counts() const { return counts_; }
    const std::vector<PackedRow>& rows() const { return rows_; }

private:
    int scope_limit_;
    bool store_rows_;
    std::array<int, 6> row_{};
    Counts counts_{};
    std::vector<PackedRow> rows_;

    void recurse(int depth, int next_minimum, Mask mask) {
        if (depth == 6) {
            ++counts_.raw_complete_choices;
            ++counts_.valid_rows;
            const int scope = row_[5];
            ++counts_.by_scope[scope];
            if (store_rows_) {
                PackedRow packed{};
                for (int i = 0; i < 6; ++i) packed.marks[i] = static_cast<std::uint8_t>(row_[i]);
                packed.scope = static_cast<std::uint8_t>(scope);
                packed.lo = mask.lo;
                packed.hi = mask.hi;
                rows_.push_back(packed);
            }
            return;
        }

        const int marks_remaining_after_current = 6 - depth - 1;
        const int max_current = scope_limit_ - marks_remaining_after_current;
        for (int candidate = next_minimum; candidate <= max_current; ++candidate) {
            ++counts_.prefixes_considered[depth - 1];
            Mask next_mask = mask;
            bool valid = true;
            for (int previous = 0; previous < depth; ++previous) {
                const int difference = candidate - row_[previous];
                if (next_mask.contains(difference)) {
                    valid = false;
                    break;
                }
                next_mask.add(difference);
            }
            if (!valid) {
                ++counts_.prefixes_pruned[depth - 1];
                continue;
            }
            row_[depth] = candidate;
            recurse(depth + 1, candidate + 1, next_mask);
        }
    }
};

static std::array<int, 6> reflected(const PackedRow& row) {
    std::array<int, 6> result{};
    for (int i = 0; i < 6; ++i) result[i] = static_cast<int>(row.scope) - static_cast<int>(row.marks[5 - i]);
    return result;
}

static bool is_canonical_reflection(const PackedRow& row) {
    const auto mirror = reflected(row);
    for (int i = 0; i < 6; ++i) {
        if (row.marks[i] < mirror[i]) return true;
        if (row.marks[i] > mirror[i]) return false;
    }
    return true;
}

static void write_catalogue(const std::string& path, int scope_limit, const std::vector<PackedRow>& rows) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("cannot open catalogue output");
    const std::uint32_t magic = 0x44545352; // DTSR
    const std::uint32_t version = 1;
    const std::uint32_t record_size = sizeof(PackedRow);
    const std::uint64_t count = rows.size();
    output.write(reinterpret_cast<const char*>(&magic), sizeof(magic));
    output.write(reinterpret_cast<const char*>(&version), sizeof(version));
    output.write(reinterpret_cast<const char*>(&scope_limit), sizeof(scope_limit));
    output.write(reinterpret_cast<const char*>(&record_size), sizeof(record_size));
    output.write(reinterpret_cast<const char*>(&count), sizeof(count));
    output.write(reinterpret_cast<const char*>(rows.data()), static_cast<std::streamsize>(rows.size() * sizeof(PackedRow)));
}

static void print_summary(int scope_limit, bool store_rows, const Counts& counts, const std::vector<PackedRow>& rows, double seconds) {
    std::uint64_t canonical = 0;
    for (const auto& row : rows) if (is_canonical_reflection(row)) ++canonical;
    std::cout << std::setprecision(12);
    std::cout << "{\"scope_limit\":" << scope_limit
              << ",\"raw_complete_choices\":" << choose5(scope_limit)
              << ",\"valid_rows\":" << counts.valid_rows
              << ",\"stored_rows\":" << rows.size()
              << ",\"reflection_representatives\":" << canonical
              << ",\"runtime_seconds\":" << seconds
              << ",\"store_rows\":" << (store_rows ? "true" : "false")
              << ",\"prefixes_considered\":[";
    for (int i = 0; i < 5; ++i) std::cout << (i ? "," : "") << counts.prefixes_considered[i];
    std::cout << "],\"prefixes_pruned\":[";
    for (int i = 0; i < 5; ++i) std::cout << (i ? "," : "") << counts.prefixes_pruned[i];
    std::cout << "],\"by_scope\":{";
    bool first = true;
    for (int scope = 1; scope <= scope_limit; ++scope) {
        if (counts.by_scope[scope] == 0) continue;
        if (!first) std::cout << ",";
        first = false;
        std::cout << "\"" << scope << "\":" << counts.by_scope[scope];
    }
    std::cout << "}}\n";
}

int main(int argc, char** argv) {
    try {
        int scope_limit = 111;
        bool store_rows = false;
        std::size_t reserve_rows = 0;
        std::string catalogue_path;
        for (int i = 1; i < argc; ++i) {
            const std::string argument = argv[i];
            if (argument == "--scope" && i + 1 < argc) scope_limit = std::stoi(argv[++i]);
            else if (argument == "--store") store_rows = true;
            else if (argument == "--reserve" && i + 1 < argc) reserve_rows = static_cast<std::size_t>(std::stoull(argv[++i]));
            else if (argument == "--catalogue" && i + 1 < argc) catalogue_path = argv[++i];
            else if (argument == "--help") {
                std::cout << "usage: enumerate_dts_rulers --scope N [--store --catalogue PATH]\n";
                return 0;
            } else throw std::runtime_error("unknown argument: " + argument);
        }
        if (scope_limit < 5 || scope_limit > 111) throw std::runtime_error("scope must be in [5,111]");
        if (!catalogue_path.empty()) store_rows = true;
        Enumerator enumerator(scope_limit, store_rows, reserve_rows);
        const auto started = std::chrono::steady_clock::now();
        enumerator.run();
        const auto finished = std::chrono::steady_clock::now();
        const double seconds = std::chrono::duration<double>(finished - started).count();
        if (!catalogue_path.empty()) write_catalogue(catalogue_path, scope_limit, enumerator.rows());
        print_summary(scope_limit, store_rows, enumerator.counts(), enumerator.rows(), seconds);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
