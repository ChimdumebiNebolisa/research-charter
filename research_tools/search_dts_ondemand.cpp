#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
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

static void set_bit(Mask& mask, int difference) {
    if (difference < 64) mask.lo |= 1ULL << difference;
    else mask.hi |= 1ULL << (difference - 64);
}

static bool add_difference(Mask& row_mask, const Mask& forbidden, int difference) {
    if (difference < 1 || difference > 111 || has_bit(forbidden, difference) || has_bit(row_mask, difference)) return false;
    set_bit(row_mask, difference);
    return true;
}

struct Generator {
    int limit;
    const Mask& used;
    const Mask& gaps;
    std::mt19937_64& rng;
    std::uint64_t node_budget;

    bool complete(std::vector<int>& marks, Mask row_mask, Row& result) {
        if (node_budget == 0) return false;
        --node_budget;
        if (marks.size() == 6) {
            std::sort(marks.begin(), marks.end());
            if (marks.front() != 0) return false;
            for (std::size_t i = 1; i < marks.size(); ++i) {
                result.marks[i] = marks[i];
            }
            result.marks[0] = 0;
            result.mask = row_mask;
            return true;
        }

        std::array<int, 111> values{};
        int value_count = 0;
        for (int value = 1; value <= limit; ++value) {
            if (std::find(marks.begin(), marks.end(), value) == marks.end()) values[value_count++] = value;
        }
        std::shuffle(values.begin(), values.begin() + value_count, rng);
        for (int index = 0; index < value_count; ++index) {
            const int value = values[index];
            Mask next_mask = row_mask;
            bool valid = true;
            for (int old : marks) {
                const int difference = std::abs(value - old);
                if (!add_difference(next_mask, used, difference) || has_bit(gaps, difference)) {
                    valid = false;
                    break;
                }
            }
            if (!valid) continue;
            marks.push_back(value);
            if (complete(marks, next_mask, result)) return true;
            marks.pop_back();
        }
        return false;
    }

    bool one(int anchor, Row& result) {
        if (anchor < 1 || anchor > limit) return false;
        const bool direct = (rng() & 3ULL) == 0 || anchor == limit;
        std::vector<int> marks{0};
        Mask row_mask;
        if (direct) {
            marks.push_back(anchor);
            if (!add_difference(row_mask, used, anchor) || has_bit(gaps, anchor)) return false;
        } else {
            std::uniform_int_distribution<int> placement(1, limit - anchor);
            const int left = placement(rng);
            marks.push_back(left);
            marks.push_back(left + anchor);
            std::sort(marks.begin(), marks.end());
            for (std::size_t right = 1; right < marks.size(); ++right) {
                for (std::size_t before = 0; before < right; ++before) {
                    if (!add_difference(row_mask, used, marks[right] - marks[before]) || has_bit(gaps, marks[right] - marks[before])) {
                        return false;
                    }
                }
            }
        }
        return complete(marks, row_mask, result);
    }
};

struct Searcher {
    int limit;
    int anchor_probe;
    int samples_per_anchor;
    std::uint64_t row_node_budget;
    bool exact_pair;
    std::uint64_t exact_pair_node_budget;
    double deadline;
    std::uint64_t node_limit;
    std::mt19937_64 rng;
    std::uint64_t nodes = 0;
    std::uint64_t generator_nodes = 0;
    std::uint64_t generated_rows = 0;
    std::uint64_t duplicate_rows = 0;
    std::uint64_t exact_pair_nodes = 0;
    std::uint64_t exact_pair_rows = 0;
    std::uint64_t exact_pair_checks = 0;
    std::uint64_t anchor_probes = 0;
    std::uint64_t gap_branches = 0;
    int best_depth = 0;
    int best_gaps = 0;
    std::vector<Row> selected;
    std::vector<Row> best_selected;
    std::vector<int> best_trace;
    bool stopped = false;

    bool expired() {
        if (clock_seconds() >= deadline || nodes >= node_limit) {
            stopped = true;
            return true;
        }
        return false;
    }

    std::vector<Row> generate(int anchor, const Mask& used, const Mask& gaps) {
        std::vector<Row> result;
        std::unordered_set<Mask, MaskHash> seen;
        seen.reserve(static_cast<std::size_t>(samples_per_anchor) * 2);
        for (int attempt = 0; attempt < samples_per_anchor && !expired(); ++attempt) {
            Generator generator{limit, used, gaps, rng, row_node_budget};
            Row row;
            if (!generator.one(anchor, row)) {
                generator_nodes += row_node_budget - generator.node_budget;
                continue;
            }
            generator_nodes += row_node_budget - generator.node_budget;
            ++generated_rows;
            if (!seen.insert(row.mask).second) {
                ++duplicate_rows;
                continue;
            }
            result.push_back(row);
        }
        std::sort(result.begin(), result.end(), [](const Row& left, const Row& right) {
            if (left.marks[5] != right.marks[5]) return left.marks[5] > right.marks[5];
            return left.marks < right.marks;
        });
        return result;
    }

    void enumerate_exact(const Mask& forbidden, std::vector<int>& marks, Mask row_mask,
                         std::vector<Row>& rows, std::uint64_t& budget) {
        if (budget == 0 || clock_seconds() >= deadline) return;
        --budget;
        ++exact_pair_nodes;
        if (marks.size() == 6) {
            Row row;
            row.marks[0] = 0;
            for (std::size_t index = 1; index < marks.size(); ++index) row.marks[index] = marks[index];
            row.mask = row_mask;
            rows.push_back(row);
            ++exact_pair_rows;
            return;
        }
        const int remaining = 6 - static_cast<int>(marks.size());
        const int low = marks.back() + 1;
        const int high = limit - remaining + 1;
        for (int value = low; value <= high; ++value) {
            Mask next = row_mask;
            bool valid = true;
            for (int old : marks) {
                const int difference = value - old;
                if (has_bit(forbidden, difference) || has_bit(next, difference)) {
                    valid = false;
                    break;
                }
                set_bit(next, difference);
            }
            if (!valid) continue;
            marks.push_back(value);
            enumerate_exact(forbidden, marks, next, rows, budget);
            marks.pop_back();
            if (budget == 0 || clock_seconds() >= deadline) return;
        }
    }

    bool exact_pair_completion(const Mask& used, const Mask& gaps, std::vector<int>& trace) {
        std::vector<Row> rows;
        std::vector<int> marks{0};
        std::uint64_t budget = exact_pair_node_budget;
        const Mask forbidden{used.lo | gaps.lo, used.hi | gaps.hi};
        enumerate_exact(forbidden, marks, Mask{}, rows, budget);
        for (std::size_t left = 0; left < rows.size(); ++left) {
            for (std::size_t right = left + 1; right < rows.size(); ++right) {
                ++exact_pair_checks;
                if (overlaps(rows[left].mask, rows[right].mask)) continue;
                best_selected = selected;
                best_selected.push_back(rows[left]);
                best_selected.push_back(rows[right]);
                best_trace = trace;
                best_trace.push_back(0);
                best_trace.push_back(0);
                return true;
            }
        }
        return false;
    }

    bool dfs(const Mask& used, const Mask& gaps, int depth, int gap_count, std::vector<int>& trace) {
        if (expired()) return false;
        if (depth > best_depth || (depth == best_depth && gap_count > best_gaps)) {
            best_depth = std::max(best_depth, depth);
            best_gaps = std::max(best_gaps, gap_count);
            best_selected = selected;
            best_trace = trace;
        }
        if (depth == 7) {
            best_selected = selected;
            best_trace = trace;
            return true;
        }
        if (exact_pair && depth == 5) {
            return exact_pair_completion(used, gaps, trace);
        }

        struct Choice { int anchor = -1; std::vector<Row> rows; } choice;
        int probes = 0;
        for (int anchor = limit; anchor >= 1 && probes < anchor_probe; --anchor) {
            if (has_bit(used, anchor) || has_bit(gaps, anchor)) continue;
            ++probes;
            ++anchor_probes;
            std::vector<Row> rows = generate(anchor, used, gaps);
            if (rows.empty()) continue;
            if (choice.anchor < 0 || rows.size() < choice.rows.size()) {
                choice.anchor = anchor;
                choice.rows = std::move(rows);
                if (choice.rows.size() == 1) break;
            }
        }
        if (choice.anchor < 0) {
            if (gap_count >= 6) return false;
            for (int anchor = limit; anchor >= 1; --anchor) {
                if (!has_bit(used, anchor) && !has_bit(gaps, anchor)) {
                    ++nodes;
                    ++gap_branches;
                    Mask next_gaps = gaps;
                    set_bit(next_gaps, anchor);
                    trace.push_back(anchor);
                    const bool found = dfs(used, next_gaps, depth, gap_count + 1, trace);
                    trace.pop_back();
                    return found;
                }
            }
            return false;
        }

        for (const Row& row : choice.rows) {
            if (expired()) return false;
            ++nodes;
            selected.push_back(row);
            Mask next_used{used.lo | row.mask.lo, used.hi | row.mask.hi};
            trace.push_back(choice.anchor);
            if (dfs(next_used, gaps, depth + 1, gap_count, trace)) return true;
            trace.pop_back();
            selected.pop_back();
        }
        if (gap_count < 6 && !expired()) {
            ++nodes;
            ++gap_branches;
            Mask next_gaps = gaps;
            set_bit(next_gaps, choice.anchor);
            trace.push_back(choice.anchor);
            if (dfs(used, next_gaps, depth, gap_count + 1, trace)) return true;
            trace.pop_back();
        }
        return false;
    }
};

struct Options {
    int limit = 111;
    int anchor_probe = 24;
    int samples_per_anchor = 18;
    std::uint64_t row_node_budget = 15000;
    bool exact_pair = false;
    std::uint64_t exact_pair_node_budget = 200000;
    double seconds = 90.0;
    std::uint64_t node_limit = 100000;
    std::uint64_t seed = 20260909;
    std::string output;
    std::string raw;
};

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i + 1 < argc; i += 2) {
        const std::string key = argv[i];
        const std::string value = argv[i + 1];
        if (key == "--limit") options.limit = std::stoi(value);
        else if (key == "--anchor-probe") options.anchor_probe = std::stoi(value);
        else if (key == "--samples-per-anchor") options.samples_per_anchor = std::stoi(value);
        else if (key == "--row-node-budget") options.row_node_budget = std::stoull(value);
        else if (key == "--exact-pair") options.exact_pair = std::stoi(value) != 0;
        else if (key == "--exact-pair-node-budget") options.exact_pair_node_budget = std::stoull(value);
        else if (key == "--seconds") options.seconds = std::stod(value);
        else if (key == "--node-limit") options.node_limit = std::stoull(value);
        else if (key == "--seed") options.seed = std::stoull(value);
        else if (key == "--output") options.output = value;
        else if (key == "--raw") options.raw = value;
    }
    if (options.output.empty() || options.raw.empty()) throw std::runtime_error("--output and --raw are required");
    return options;
}

static void write_rows(std::ostream& out, const std::vector<Row>& rows) {
    out << "[";
    for (std::size_t i = 0; i < rows.size(); ++i) {
        if (i) out << ",";
        out << "[";
        for (int j = 0; j < 6; ++j) {
            if (j) out << ",";
            out << rows[i].marks[j];
        }
        out << "]";
    }
    out << "]";
}

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const double started = clock_seconds();
        Searcher searcher{options.limit, options.anchor_probe, options.samples_per_anchor, options.row_node_budget,
                          options.exact_pair, options.exact_pair_node_budget, started + options.seconds,
                          options.node_limit, std::mt19937_64(options.seed)};
        Mask empty;
        std::vector<int> trace;
        const bool found = searcher.dfs(empty, empty, 0, 0, trace);
        const double elapsed = clock_seconds() - started;

        std::ofstream artifact(options.output);
        artifact << "{\"method\":\"ondemand-incremental-compatible-row-exact-cover\",\"status\":\"completed\",\"limit\":"
                  << options.limit << ",\"anchor_probe\":" << options.anchor_probe
                  << ",\"samples_per_anchor\":" << options.samples_per_anchor
                  << ",\"row_node_budget\":" << options.row_node_budget
                  << ",\"exact_pair\":" << (options.exact_pair ? "true" : "false")
                  << ",\"exact_pair_node_budget\":" << options.exact_pair_node_budget
                  << ",\"seconds\":" << options.seconds << ",\"node_limit\":" << options.node_limit
                  << ",\"seed\":" << options.seed << ",\"search_nodes\":" << searcher.nodes
                  << ",\"generator_nodes\":" << searcher.generator_nodes << ",\"generated_rows\":" << searcher.generated_rows
                  << ",\"duplicate_rows\":" << searcher.duplicate_rows
                  << ",\"exact_pair_nodes\":" << searcher.exact_pair_nodes
                  << ",\"exact_pair_rows\":" << searcher.exact_pair_rows
                  << ",\"exact_pair_checks\":" << searcher.exact_pair_checks
                  << ",\"anchor_probes\":" << searcher.anchor_probes
                  << ",\"gap_branches\":" << searcher.gap_branches << ",\"best_depth\":" << searcher.best_depth
                  << ",\"best_gaps\":" << searcher.best_gaps << ",\"stopped\":" << (searcher.stopped ? "true" : "false")
                  << ",\"target_reached\":" << (found ? "true" : "false")
                  << ",\"elapsed_seconds\":" << std::setprecision(12) << elapsed << ",\"rows\":";
        write_rows(artifact, searcher.best_selected);
        artifact << ",\"anchor_trace\":[";
        for (std::size_t i = 0; i < searcher.best_trace.size(); ++i) {
            if (i) artifact << ",";
            artifact << searcher.best_trace[i];
        }
        artifact << "]}\n";

        std::ofstream raw(options.raw);
        raw << "Experiment dts-ondemand-constrained-rows-001 execution record\n"
            << "Method: dynamically generate rows from the current unused-difference mask; reject conflicts while adding marks; branch on sampled scarce anchors\n"
            << "Seed: " << options.seed << "; anchor probes: " << options.anchor_probe << "; samples per anchor: " << options.samples_per_anchor << "\n"
            << "Search nodes: " << searcher.nodes << "; generator nodes: " << searcher.generator_nodes << "; generated rows: " << searcher.generated_rows << "\n"
            << "Exact-pair mode: " << (options.exact_pair ? "true" : "false") << "; exact-pair nodes: " << searcher.exact_pair_nodes
            << "; exact-pair rows: " << searcher.exact_pair_rows << "; exact-pair checks: " << searcher.exact_pair_checks << "\n"
            << "Best depth: " << searcher.best_depth << "; best gaps: " << searcher.best_gaps << "; gap branches: " << searcher.gap_branches << "\n"
            << "Target reached: " << (found ? "true" : "false") << "\nRows: ";
        write_rows(raw, searcher.best_selected);
        raw << "\nAnchor trace: ";
        for (std::size_t i = 0; i < searcher.best_trace.size(); ++i) {
            if (i) raw << ",";
            raw << searcher.best_trace[i];
        }
        raw << "\nElapsed seconds: " << std::setprecision(12) << elapsed << "\n";
        std::cout << "seed=" << options.seed << " nodes=" << searcher.nodes << " generated_rows=" << searcher.generated_rows
                  << " best_depth=" << searcher.best_depth << " best_gaps=" << searcher.best_gaps
                  << " target=" << (found ? "true" : "false") << " elapsed=" << elapsed << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
