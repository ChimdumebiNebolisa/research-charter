#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <sstream>
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

struct Searcher {
    const std::vector<Row>& rows;
    const std::vector<std::vector<int>>& by_difference;
    double deadline;
    std::uint64_t node_limit;
    std::uint64_t nodes = 0;
    int best_depth = 0;
    int best_gaps = 0;
    std::vector<int> selected;
    std::vector<int> best_selected;
    bool stopped = false;

    static bool has_bit(const Mask& mask, int difference) {
        if (difference < 64) return (mask.lo & (1ULL << difference)) != 0;
        return (mask.hi & (1ULL << (difference - 64))) != 0;
    }

    static bool overlaps(const Mask& left, const Mask& right) {
        return ((left.lo & right.lo) != 0) || ((left.hi & right.hi) != 0);
    }

    bool expired() const {
        const double now = std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
        return now >= deadline || nodes >= node_limit;
    }

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
        std::size_t anchor_count = static_cast<std::size_t>(-1);
        for (int difference = 1; difference <= 111; ++difference) {
            if (has_bit(used, difference) || has_bit(gaps, difference)) continue;
            std::size_t compatible = 0;
            for (int row_id : by_difference[difference]) {
                const Mask& mask = rows[row_id].mask;
                if (!overlaps(mask, used) && !overlaps(mask, gaps)) ++compatible;
            }
            if (compatible < anchor_count) {
                anchor = difference;
                anchor_count = compatible;
                if (anchor_count == 0) break;
            }
        }
        if (anchor < 0) return false;

        std::vector<int> candidates;
        candidates.reserve(anchor_count);
        for (int row_id : by_difference[anchor]) {
            const Mask& mask = rows[row_id].mask;
            if (!overlaps(mask, used) && !overlaps(mask, gaps)) candidates.push_back(row_id);
        }
        std::sort(candidates.begin(), candidates.end(), [&](int left, int right) {
            if (rows[left].rarity != rows[right].rarity) return rows[left].rarity > rows[right].rarity;
            return left < right;
        });

        for (int row_id : candidates) {
            if (expired()) {
                stopped = true;
                return false;
            }
            ++nodes;
            selected.push_back(row_id);
            Mask next_used{used.lo | rows[row_id].mask.lo, used.hi | rows[row_id].mask.hi};
            if (dfs(next_used, gaps, depth + 1, gap_count)) return true;
            selected.pop_back();
        }

        if (gap_count < 6) {
            Mask next_gaps{gaps.lo, gaps.hi};
            if (anchor < 64) next_gaps.lo |= 1ULL << anchor;
            else next_gaps.hi |= 1ULL << (anchor - 64);
            ++nodes;
            if (dfs(used, next_gaps, depth, gap_count + 1)) return true;
        }
        return false;
    }
};

struct Options {
    int limit = 111;
    int catalog_size = 1000000;
    std::uint64_t attempt_limit = 10000000;
    double seconds = 360.0;
    std::uint64_t node_limit = 100000000;
    std::uint64_t seed = 20260827;
    std::string output;
    std::string raw;
};

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i + 1 < argc; i += 2) {
        const std::string key = argv[i];
        const std::string value = argv[i + 1];
        if (key == "--catalog-size") options.catalog_size = std::stoi(value);
        else if (key == "--attempt-limit") options.attempt_limit = std::stoull(value);
        else if (key == "--seconds") options.seconds = std::stod(value);
        else if (key == "--node-limit") options.node_limit = std::stoull(value);
        else if (key == "--seed") options.seed = std::stoull(value);
        else if (key == "--output") options.output = value;
        else if (key == "--raw") options.raw = value;
    }
    if (options.output.empty() || options.raw.empty()) {
        throw std::runtime_error("--output and --raw are required");
    }
    return options;
}

bool sample_row(std::mt19937_64& rng, int limit, Row& result) {
    std::array<int, 5> marks{};
    for (int i = 0; i < 5; ++i) marks[i] = i + 1;
    std::uniform_int_distribution<int> distribution(1, limit);
    std::unordered_set<int> seen;
    for (int i = 0; i < 5; ++i) {
        int value;
        do value = distribution(rng); while (!seen.insert(value).second);
        marks[i] = value;
    }
    std::sort(marks.begin(), marks.end());
    Mask mask;
    for (int left = 0; left < 6; ++left) {
        const int left_value = left == 0 ? 0 : marks[left - 1];
        for (int right = left + 1; right < 6; ++right) {
            const int right_value = right == 0 ? 0 : marks[right - 1];
            const int difference = right_value - left_value;
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

void write_rows(std::ostream& out, const std::vector<Row>& rows, const std::vector<int>& selected) {
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

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const double started = std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
        const double deadline = started + options.seconds;
        std::mt19937_64 rng(options.seed);
        std::vector<Row> rows;
        rows.reserve(options.catalog_size);
        std::unordered_set<Mask, MaskHash> masks;
        masks.reserve(static_cast<std::size_t>(options.catalog_size) * 2);
        std::uint64_t attempts = 0;
        std::uint64_t valid = 0;
        while (static_cast<int>(rows.size()) < options.catalog_size && attempts < options.attempt_limit) {
            if (std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count() >= deadline) break;
            ++attempts;
            Row row;
            if (!sample_row(rng, options.limit, row)) continue;
            ++valid;
            if (masks.insert(row.mask).second) rows.push_back(row);
        }

        std::vector<int> frequencies(options.limit + 1, 0);
        for (const Row& row : rows) {
            for (int difference = 1; difference <= options.limit; ++difference) {
                if (Searcher::has_bit(row.mask, difference)) ++frequencies[difference];
            }
        }
        std::vector<std::vector<int>> by_difference(options.limit + 1);
        for (int row_id = 0; row_id < static_cast<int>(rows.size()); ++row_id) {
            double rarity = 0.0;
            for (int difference = 1; difference <= options.limit; ++difference) {
                if (Searcher::has_bit(rows[row_id].mask, difference)) {
                    by_difference[difference].push_back(row_id);
                    rarity += 1.0 / std::max(1, frequencies[difference]);
                }
            }
            rows[row_id].rarity = rarity;
        }

        Searcher searcher{rows, by_difference, deadline, options.node_limit};
        Mask empty;
        const bool found = searcher.dfs(empty, empty, 0, 0);
        const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count() - started;
        std::ofstream artifact(options.output);
        artifact << "{\"method\":\"cpp-random-golomb-catalog-adaptive-exact-cover\",\"status\":\"completed\",\"limit\":" << options.limit
                 << ",\"catalog_size\":" << rows.size() << ",\"catalog_target\":" << options.catalog_size
                 << ",\"attempts\":" << attempts << ",\"valid_generated\":" << valid
                 << ",\"node_limit\":" << options.node_limit << ",\"search_nodes\":" << searcher.nodes
                 << ",\"best_depth\":" << searcher.best_depth << ",\"best_gaps\":" << searcher.best_gaps
                 << ",\"stopped\":" << (searcher.stopped ? "true" : "false") << ",\"target_reached\":" << (found ? "true" : "false")
                 << ",\"elapsed_seconds\":" << std::setprecision(12) << elapsed << ",\"rows\":";
        write_rows(artifact, rows, found ? searcher.best_selected : std::vector<int>{});
        artifact << "}\n";
        std::ofstream raw(options.raw);
        raw << "Experiment dts-cpp-exact-cover-001 execution record\n"
            << "Method: 64-bit exact difference masks, deduplicated random Golomb catalogue, rare compatible-difference branching\n"
            << "Catalog size: " << rows.size() << "; attempts: " << attempts << "; valid generated: " << valid << "\n"
            << "Search nodes: " << searcher.nodes << "; best depth: " << searcher.best_depth << "; best gaps: " << searcher.best_gaps << "\n"
            << "Target reached: " << (found ? "true" : "false") << "\nRows: ";
        write_rows(raw, rows, found ? searcher.best_selected : std::vector<int>{});
        raw << "\nElapsed seconds: " << std::setprecision(12) << elapsed << "\n";
        std::cout << "catalog=" << rows.size() << " attempts=" << attempts << " nodes=" << searcher.nodes
                  << " best_depth=" << searcher.best_depth << " target=" << (found ? "true" : "false") << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
