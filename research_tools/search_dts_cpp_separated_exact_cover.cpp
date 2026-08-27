#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

struct Mask {
    std::uint64_t lo = 0;
    std::uint64_t hi = 0;
    bool operator==(const Mask& other) const { return lo == other.lo && hi == other.hi; }
};

struct MaskHash {
    std::size_t operator()(const Mask& mask) const {
        std::uint64_t x = mask.lo ^ (mask.hi + 0x9e3779b97f4a7c15ULL + (mask.lo << 6) + (mask.lo >> 2));
        x ^= x >> 30;
        x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27;
        x *= 0x94d049bb133111ebULL;
        return static_cast<std::size_t>(x ^ (x >> 31));
    }
};

struct Row {
    Mask mask;
    std::array<int, 6> marks{};
    double rarity = 0.0;
};

static double clock_seconds() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

static bool has_bit(const Mask& mask, int difference) {
    if (difference < 64) return (mask.lo & (1ULL << difference)) != 0;
    return (mask.hi & (1ULL << (difference - 64))) != 0;
}

static bool overlaps(const Mask& left, const Mask& right) {
    return ((left.lo & right.lo) != 0) || ((left.hi & right.hi) != 0);
}

static bool sample_row(std::mt19937_64& rng, int limit, Row& result) {
    std::array<int, 5> marks{};
    std::uniform_int_distribution<int> distribution(1, limit);
    for (int i = 0; i < 5; ++i) {
        int value;
        bool duplicate;
        do {
            value = distribution(rng);
            duplicate = false;
            for (int j = 0; j < i; ++j) duplicate = duplicate || marks[j] == value;
        } while (duplicate);
        marks[i] = value;
    }
    std::sort(marks.begin(), marks.end());
    Mask mask;
    for (int left = 0; left < 6; ++left) {
        const int left_value = left == 0 ? 0 : marks[left - 1];
        for (int right = left + 1; right < 6; ++right) {
            const int difference = marks[right - 1] - left_value;
            if (difference < 1 || difference > limit) return false;
            if (difference < 64) {
                const std::uint64_t bit = 1ULL << difference;
                if (mask.lo & bit) return false;
                mask.lo |= bit;
            } else {
                const std::uint64_t bit = 1ULL << (difference - 64);
                if (mask.hi & bit) return false;
                mask.hi |= bit;
            }
        }
    }
    result.mask = mask;
    result.marks[0] = 0;
    for (int i = 0; i < 5; ++i) result.marks[i + 1] = marks[i];
    return true;
}

struct Options {
    int limit = 111;
    int catalog_size = 1000000;
    std::uint64_t attempt_limit = 10000000;
    std::uint64_t node_limit = 100000000;
    std::uint64_t seed = 20260828;
    double seconds = 120.0;
    std::string mode;
    std::string catalog;
    std::string output;
    std::string raw;
};

static Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i + 1 < argc; i += 2) {
        const std::string key = argv[i];
        const std::string value = argv[i + 1];
        if (key == "--mode") options.mode = value;
        else if (key == "--limit") options.limit = std::stoi(value);
        else if (key == "--catalog-size") options.catalog_size = std::stoi(value);
        else if (key == "--attempt-limit") options.attempt_limit = std::stoull(value);
        else if (key == "--node-limit") options.node_limit = std::stoull(value);
        else if (key == "--seed") options.seed = std::stoull(value);
        else if (key == "--seconds") options.seconds = std::stod(value);
        else if (key == "--catalog") options.catalog = value;
        else if (key == "--output") options.output = value;
        else if (key == "--raw") options.raw = value;
    }
    if (options.mode != "generate" && options.mode != "search") throw std::runtime_error("--mode must be generate or search");
    if (options.catalog.empty()) throw std::runtime_error("--catalog is required");
    if (options.mode == "generate" && options.catalog_size <= 0) throw std::runtime_error("--catalog-size must be positive");
    if (options.mode == "search" && (options.output.empty() || options.raw.empty())) throw std::runtime_error("--output and --raw are required for search");
    return options;
}

static void write_catalog(const std::string& path, int limit, const std::vector<Row>& rows) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) throw std::runtime_error("cannot open catalogue for writing");
    const char magic[8] = {'D', 'T', 'S', 'C', 'P', 'P', '2', 0};
    const std::uint32_t version = 1;
    const std::uint32_t count = static_cast<std::uint32_t>(rows.size());
    const std::uint32_t stored_limit = static_cast<std::uint32_t>(limit);
    out.write(magic, sizeof magic);
    out.write(reinterpret_cast<const char*>(&version), sizeof version);
    out.write(reinterpret_cast<const char*>(&stored_limit), sizeof stored_limit);
    out.write(reinterpret_cast<const char*>(&count), sizeof count);
    for (const Row& row : rows) {
        out.write(reinterpret_cast<const char*>(row.marks.data()), sizeof row.marks);
        out.write(reinterpret_cast<const char*>(&row.mask), sizeof row.mask);
    }
    if (!out) throw std::runtime_error("catalogue write failed");
}

static std::vector<Row> read_catalog(const std::string& path, int expected_limit) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open catalogue for reading");
    char magic[8]{};
    std::uint32_t version = 0;
    std::uint32_t limit = 0;
    std::uint32_t count = 0;
    in.read(magic, sizeof magic);
    in.read(reinterpret_cast<char*>(&version), sizeof version);
    in.read(reinterpret_cast<char*>(&limit), sizeof limit);
    in.read(reinterpret_cast<char*>(&count), sizeof count);
    const char expected_magic[8] = {'D', 'T', 'S', 'C', 'P', 'P', '2', 0};
    if (std::memcmp(magic, expected_magic, sizeof magic) != 0 || version != 1 || limit != static_cast<std::uint32_t>(expected_limit)) {
        throw std::runtime_error("invalid catalogue header");
    }
    std::vector<Row> rows(count);
    for (Row& row : rows) {
        in.read(reinterpret_cast<char*>(row.marks.data()), sizeof row.marks);
        in.read(reinterpret_cast<char*>(&row.mask), sizeof row.mask);
    }
    if (!in) throw std::runtime_error("catalogue read failed");
    return rows;
}

static void write_rows(std::ostream& out, const std::vector<Row>& rows, const std::vector<int>& selected) {
    out << "[";
    for (std::size_t i = 0; i < selected.size(); ++i) {
        if (i) out << ",";
        out << "[";
        for (int j = 0; j < 6; ++j) {
            if (j) out << ",";
            out << rows[selected[i]].marks[j];
        }
        out << "]";
    }
    out << "]";
}

struct Searcher {
    const std::vector<Row>& rows;
    const std::vector<std::vector<int>>& by_difference;
    std::vector<int> static_order;
    double deadline;
    std::uint64_t node_limit;
    std::uint64_t nodes = 0;
    int best_depth = 0;
    int best_gaps = 0;
    bool stopped = false;
    std::vector<int> selected;
    std::vector<int> best_selected;

    bool expired() const { return clock_seconds() >= deadline || nodes >= node_limit; }

    bool dfs(const Mask& used, const Mask& gaps, int depth, int gap_count) {
        best_depth = std::max(best_depth, depth);
        best_gaps = std::max(best_gaps, gap_count);
        if (expired()) {
            stopped = true;
            return false;
        }
        if (depth == 7) {
            best_selected = selected;
            return true;
        }

        int anchor = -1;
        for (int difference : static_order) {
            if (has_bit(used, difference) || has_bit(gaps, difference)) continue;
            anchor = difference;
            bool has_compatible = false;
            for (int row_id : by_difference[difference]) {
                if (!overlaps(rows[row_id].mask, used) && !overlaps(rows[row_id].mask, gaps)) {
                    has_compatible = true;
                    break;
                }
            }
            if (has_compatible) break;
        }
        if (anchor < 0) return false;

        std::vector<int> candidates;
        for (int row_id : by_difference[anchor]) {
            if (!overlaps(rows[row_id].mask, used) && !overlaps(rows[row_id].mask, gaps)) candidates.push_back(row_id);
        }
        for (int row_id : candidates) {
            if (expired()) {
                stopped = true;
                return false;
            }
            ++nodes;
            selected.push_back(row_id);
            const Mask next_used{used.lo | rows[row_id].mask.lo, used.hi | rows[row_id].mask.hi};
            if (dfs(next_used, gaps, depth + 1, gap_count)) return true;
            selected.pop_back();
        }
        if (gap_count < 6) {
            Mask next_gaps = gaps;
            if (anchor < 64) next_gaps.lo |= 1ULL << anchor;
            else next_gaps.hi |= 1ULL << (anchor - 64);
            ++nodes;
            if (dfs(used, next_gaps, depth, gap_count + 1)) return true;
        }
        return false;
    }
};

static int generate(const Options& options) {
    const double started = clock_seconds();
    const double deadline = started + options.seconds;
    std::mt19937_64 rng(options.seed);
    std::vector<Row> rows;
    rows.reserve(options.catalog_size);
    std::unordered_set<Mask, MaskHash> masks;
    masks.reserve(static_cast<std::size_t>(options.catalog_size) * 2);
    std::uint64_t attempts = 0;
    std::uint64_t valid = 0;
    while (static_cast<int>(rows.size()) < options.catalog_size && attempts < options.attempt_limit && clock_seconds() < deadline) {
        ++attempts;
        Row row;
        if (!sample_row(rng, options.limit, row)) continue;
        ++valid;
        if (masks.insert(row.mask).second) rows.push_back(row);
    }
    write_catalog(options.catalog, options.limit, rows);
    std::cout << "mode=generate catalog=" << rows.size() << " attempts=" << attempts << " valid=" << valid
              << " elapsed=" << std::setprecision(12) << (clock_seconds() - started) << "\n";
    return 0;
}

static int search(const Options& options) {
    const double started = clock_seconds();
    const double deadline = started + options.seconds;
    std::vector<Row> rows = read_catalog(options.catalog, options.limit);
    std::vector<int> frequencies(options.limit + 1, 0);
    for (const Row& row : rows) {
        for (int difference = 1; difference <= options.limit; ++difference) {
            if (has_bit(row.mask, difference)) ++frequencies[difference];
        }
    }
    std::vector<std::vector<int>> by_difference(options.limit + 1);
    for (int row_id = 0; row_id < static_cast<int>(rows.size()); ++row_id) {
        double rarity = 0.0;
        for (int difference = 1; difference <= options.limit; ++difference) {
            if (has_bit(rows[row_id].mask, difference)) {
                by_difference[difference].push_back(row_id);
                rarity += 1.0 / std::max(1, frequencies[difference]);
            }
        }
        rows[row_id].rarity = rarity;
    }
    std::vector<int> static_order;
    for (int difference = 1; difference <= options.limit; ++difference) static_order.push_back(difference);
    std::sort(static_order.begin(), static_order.end(), [&](int left, int right) {
        if (frequencies[left] != frequencies[right]) return frequencies[left] < frequencies[right];
        return left < right;
    });
    for (int difference = 1; difference <= options.limit; ++difference) {
        std::sort(by_difference[difference].begin(), by_difference[difference].end(), [&](int left, int right) {
            if (rows[left].rarity != rows[right].rarity) return rows[left].rarity > rows[right].rarity;
            return left < right;
        });
    }

    Searcher searcher{rows, by_difference, static_order, deadline, options.node_limit};
    const Mask empty;
    const bool found = searcher.dfs(empty, empty, 0, 0);
    const double elapsed = clock_seconds() - started;
    std::ofstream artifact(options.output);
    artifact << "{\"method\":\"cpp-separated-catalog-static-rare-exact-cover\",\"status\":\"completed\",\"limit\":" << options.limit
             << ",\"catalog_size\":" << rows.size() << ",\"node_limit\":" << options.node_limit
             << ",\"search_nodes\":" << searcher.nodes << ",\"best_depth\":" << searcher.best_depth
             << ",\"best_gaps\":" << searcher.best_gaps << ",\"stopped\":" << (searcher.stopped ? "true" : "false")
             << ",\"target_reached\":" << (found ? "true" : "false") << ",\"elapsed_seconds\":" << std::setprecision(12) << elapsed << ",\"rows\":";
    write_rows(artifact, rows, found ? searcher.best_selected : std::vector<int>{});
    artifact << "}\n";
    std::ofstream raw(options.raw);
    raw << "Experiment dts-separated-catalog-exact-cover-001 search record\n"
        << "Method: persistent catalogue plus static rare-difference branching\n"
        << "Catalog size: " << rows.size() << "\n"
        << "Search nodes: " << searcher.nodes << "; best depth: " << searcher.best_depth << "; best gaps: " << searcher.best_gaps << "\n"
        << "Target reached: " << (found ? "true" : "false") << "\nRows: ";
    write_rows(raw, rows, found ? searcher.best_selected : std::vector<int>{});
    raw << "\nElapsed seconds: " << std::setprecision(12) << elapsed << "\n";
    std::cout << "mode=search catalog=" << rows.size() << " nodes=" << searcher.nodes << " best_depth=" << searcher.best_depth
              << " target=" << (found ? "true" : "false") << " elapsed=" << std::setprecision(12) << elapsed << "\n";
    return 0;
}

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        return options.mode == "generate" ? generate(options) : search(options);
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
