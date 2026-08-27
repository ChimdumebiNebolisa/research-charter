#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

using Row = std::array<int, 6>;

struct Mask {
    std::uint64_t lo = 0;
    std::uint64_t hi = 0;
};

static double clock_seconds() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

static bool has_bit(const Mask& mask, int difference) {
    if (difference < 64) return (mask.lo & (1ULL << difference)) != 0;
    return (mask.hi & (1ULL << (difference - 64))) != 0;
}

static void set_bit(Mask& mask, int difference) {
    if (difference < 64) mask.lo |= 1ULL << difference;
    else mask.hi |= 1ULL << (difference - 64);
}

static bool overlaps(const Mask& left, const Mask& right) {
    return (left.lo & right.lo) != 0 || (left.hi & right.hi) != 0;
}

static Mask row_mask(const Row& row, bool& valid) {
    Mask mask;
    valid = row[0] == 0;
    for (int right = 1; right < 6 && valid; ++right) {
        valid = row[right - 1] < row[right];
        for (int left = 0; left < right && valid; ++left) {
            const int difference = row[right] - row[left];
            if (difference < 1 || difference > 111 || has_bit(mask, difference)) valid = false;
            else set_bit(mask, difference);
        }
    }
    return mask;
}

struct Enumerator {
    int limit;
    const Mask& available;
    double deadline;
    std::uint64_t node_limit;
    std::uint64_t nodes = 0;
    bool stopped = false;
    std::vector<Row> rows;

    bool expired() {
        if (clock_seconds() >= deadline || nodes >= node_limit) {
            stopped = true;
            return true;
        }
        return false;
    }

    void visit(std::vector<int>& marks, Mask local_mask) {
        if (expired()) return;
        ++nodes;
        if (marks.size() == 6) {
            Row row{};
            for (std::size_t index = 0; index < marks.size(); ++index) row[index] = marks[index];
            rows.push_back(row);
            return;
        }
        const int remaining = 6 - static_cast<int>(marks.size());
        const int low = marks.back() + 1;
        const int high = limit - remaining + 1;
        for (int value = low; value <= high; ++value) {
            Mask next = local_mask;
            bool valid = true;
            for (int old : marks) {
                const int difference = value - old;
                if (!has_bit(available, difference) || has_bit(next, difference)) {
                    valid = false;
                    break;
                }
                set_bit(next, difference);
            }
            if (!valid) continue;
            marks.push_back(value);
            visit(marks, next);
            marks.pop_back();
            if (stopped) return;
        }
    }
};

static const std::array<Row, 7> BASELINE = {{
    Row{0, 11, 58, 75, 98, 111},
    Row{0, 12, 32, 50, 103, 111},
    Row{0, 22, 41, 89, 104, 110},
    Row{0, 28, 52, 83, 108, 109},
    Row{0, 13, 62, 72, 105, 107},
    Row{0, 9, 16, 60, 102, 106},
    Row{0, 27, 30, 66, 95, 100},
}};

struct Options {
    int limit = 111;
    double seconds = 120.0;
    std::uint64_t node_limit = 1000000000ULL;
    std::string output;
    std::string raw;
};

Options parse_options(int argc, char** argv) {
    Options options;
    for (int index = 1; index + 1 < argc; index += 2) {
        const std::string key = argv[index];
        const std::string value = argv[index + 1];
        if (key == "--limit") options.limit = std::stoi(value);
        else if (key == "--seconds") options.seconds = std::stod(value);
        else if (key == "--node-limit") options.node_limit = std::stoull(value);
        else if (key == "--output") options.output = value;
        else if (key == "--raw") options.raw = value;
    }
    if (options.output.empty() || options.raw.empty()) throw std::runtime_error("--output and --raw are required");
    return options;
}

static void write_row(std::ostream& out, const Row& row) {
    out << "[";
    for (int index = 0; index < 6; ++index) {
        if (index) out << ",";
        out << row[index];
    }
    out << "]";
}

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const double started = clock_seconds();
        std::uint64_t nodes = 0;
        std::uint64_t candidates = 0;
        std::uint64_t triple_checks = 0;
        std::uint64_t consistent_cases = 0;
        std::uint64_t inconsistent_cases = 0;
        bool stopped = false;
        bool found = false;
        std::array<int, 3> found_omitted{-1, -1, -1};
        std::array<Row, 3> found_rows{};
        std::vector<std::array<int, 3>> consistent_triples;
        std::vector<std::uint64_t> nodes_by_case;
        std::vector<std::uint64_t> rows_by_case;
        std::vector<std::uint64_t> triples_by_case;

        for (int first = 0; first < 7 && !stopped && !found; ++first) {
            for (int second = first + 1; second < 7 && !stopped && !found; ++second) {
                for (int third = second + 1; third < 7 && !stopped && !found; ++third) {
                    Mask fixed_mask;
                    bool consistent = true;
                    for (int index = 0; index < 7; ++index) {
                        if (index == first || index == second || index == third) continue;
                        bool valid = false;
                        const Mask mask = row_mask(BASELINE[index], valid);
                        if (!valid || overlaps(fixed_mask, mask)) consistent = false;
                        fixed_mask.lo |= mask.lo;
                        fixed_mask.hi |= mask.hi;
                    }
                    if (!consistent) {
                        ++inconsistent_cases;
                        continue;
                    }
                    ++consistent_cases;
                    consistent_triples.push_back({first, second, third});
                    Mask available;
                    for (int difference = 1; difference <= options.limit; ++difference) {
                        if (!has_bit(fixed_mask, difference)) set_bit(available, difference);
                    }
                    Enumerator enumerator{options.limit, available, started + options.seconds, options.node_limit};
                    std::vector<int> marks{0};
                    enumerator.visit(marks, Mask{});
                    nodes += enumerator.nodes;
                    candidates += enumerator.rows.size();
                    nodes_by_case.push_back(enumerator.nodes);
                    rows_by_case.push_back(enumerator.rows.size());
                    std::uint64_t case_triples = 0;
                    for (std::size_t a = 0; a < enumerator.rows.size() && !found; ++a) {
                        bool valid_a = false;
                        const Mask mask_a = row_mask(enumerator.rows[a], valid_a);
                        if (!valid_a) continue;
                        for (std::size_t b = a + 1; b < enumerator.rows.size() && !found; ++b) {
                            bool valid_b = false;
                            const Mask mask_b = row_mask(enumerator.rows[b], valid_b);
                            if (!valid_b || overlaps(mask_a, mask_b)) continue;
                            for (std::size_t c = b + 1; c < enumerator.rows.size(); ++c) {
                                ++triple_checks;
                                ++case_triples;
                                bool valid_c = false;
                                const Mask mask_c = row_mask(enumerator.rows[c], valid_c);
                                if (!valid_c || overlaps(mask_a, mask_c) || overlaps(mask_b, mask_c)) continue;
                                found = true;
                                found_omitted = {first, second, third};
                                found_rows = {enumerator.rows[a], enumerator.rows[b], enumerator.rows[c]};
                                break;
                            }
                        }
                    }
                    triples_by_case.push_back(case_triples);
                    stopped = enumerator.stopped;
                }
            }
        }

        const double elapsed = clock_seconds() - started;
        std::ofstream artifact(options.output);
        artifact << "{\"method\":\"exhaustive-global-three-row-replacement\",\"status\":\"completed\",\"limit\":" << options.limit
                  << ",\"seconds\":" << options.seconds << ",\"node_limit\":" << options.node_limit
                  << ",\"consistent_cases\":" << consistent_cases << ",\"inconsistent_cases\":" << inconsistent_cases
                  << ",\"nodes\":" << nodes << ",\"complete_compatible_rows\":" << candidates
                  << ",\"triple_checks\":" << triple_checks << ",\"stopped\":" << (stopped ? "true" : "false")
                  << ",\"target_reached\":" << (found ? "true" : "false") << ",\"found_omitted_triple\":["
                  << found_omitted[0] << "," << found_omitted[1] << "," << found_omitted[2] << "],\"found_rows\":[";
        for (int index = 0; index < 3 && found; ++index) {
            if (index) artifact << ",";
            write_row(artifact, found_rows[index]);
        }
        artifact << "],\"consistent_triples\":[";
        for (std::size_t index = 0; index < consistent_triples.size(); ++index) {
            if (index) artifact << ",";
            artifact << "[" << consistent_triples[index][0] << "," << consistent_triples[index][1] << "," << consistent_triples[index][2] << "]";
        }
        artifact << "],\"nodes_by_case\":[";
        for (std::size_t index = 0; index < nodes_by_case.size(); ++index) {
            if (index) artifact << ",";
            artifact << nodes_by_case[index];
        }
        artifact << "],\"rows_by_case\":[";
        for (std::size_t index = 0; index < rows_by_case.size(); ++index) {
            if (index) artifact << ",";
            artifact << rows_by_case[index];
        }
        artifact << "]}\n";

        std::ofstream raw(options.raw);
        raw << "Experiment dts-three-row-replacement-001 execution record\n"
            << "Method: exhaustive enumeration of every compatible row triple after fixing four clamped published rows\n"
            << "Consistent cases: " << consistent_cases << "; inconsistent cases: " << inconsistent_cases << "; nodes: " << nodes
            << "; complete compatible rows: " << candidates << "; triple checks: " << triple_checks << "\n"
            << "Target reached: " << (found ? "true" : "false") << "\nOmitted triple: [" << found_omitted[0] << "," << found_omitted[1] << "," << found_omitted[2] << "]\nRows: ";
        for (int index = 0; index < 3 && found; ++index) {
            if (index) raw << ",";
            write_row(raw, found_rows[index]);
        }
        raw << "\nElapsed seconds: " << std::setprecision(12) << elapsed << "\n";
        std::cout << "target=" << (found ? "true" : "false") << " consistent_cases=" << consistent_cases
                  << " complete_rows=" << candidates << " triple_checks=" << triple_checks << " elapsed=" << elapsed << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
