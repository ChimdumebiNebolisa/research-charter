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

static bool overlaps(const Mask& left, const Mask& right) {
    return (left.lo & right.lo) != 0 || (left.hi & right.hi) != 0;
}

struct Enumerator {
    int limit;
    const Mask& available;
    double deadline;
    std::uint64_t node_limit;
    std::uint64_t nodes = 0;
    std::uint64_t complete_rows = 0;
    std::uint64_t compatible_rows = 0;
    bool stopped = false;
    bool found = false;
    Row candidate{};

    bool expired() {
        if (clock_seconds() >= deadline || nodes >= node_limit) {
            stopped = true;
            return true;
        }
        return false;
    }

    bool visit(std::vector<int>& marks, Mask used) {
        if (expired()) return false;
        ++nodes;
        if (marks.size() == 6) {
            ++complete_rows;
            candidate[0] = 0;
            for (std::size_t i = 1; i < marks.size(); ++i) candidate[i] = marks[i];
            ++compatible_rows;
            found = true;
            return true;
        }

        const int remaining = 6 - static_cast<int>(marks.size());
        const int low = marks.back() + 1;
        const int high = limit - remaining + 1;
        for (int value = low; value <= high; ++value) {
            Mask next = used;
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
            if (visit(marks, next)) return true;
            marks.pop_back();
        }
        return false;
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
    for (int i = 1; i + 1 < argc; i += 2) {
        const std::string key = argv[i];
        const std::string value = argv[i + 1];
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
        std::vector<std::uint64_t> nodes(7, 0);
        std::vector<std::uint64_t> complete_rows(7, 0);
        std::vector<std::uint64_t> compatible_rows(7, 0);
        std::vector<bool> fixed_consistent(7, true);
        std::vector<Row> found_rows;
        bool stopped = false;

        for (int omitted = 0; omitted < 7 && !stopped && found_rows.empty(); ++omitted) {
            Mask fixed_mask;
            bool consistent = true;
            for (int index = 0; index < 7; ++index) {
                if (index == omitted) continue;
                bool valid = false;
                const Mask mask = row_mask(BASELINE[index], valid);
                if (!valid || overlaps(fixed_mask, mask)) consistent = false;
                fixed_mask.lo |= mask.lo;
                fixed_mask.hi |= mask.hi;
            }
            fixed_consistent[omitted] = consistent;
            if (!consistent) continue;

            Mask available;
            for (int difference = 1; difference <= options.limit; ++difference) {
                if (!has_bit(fixed_mask, difference)) set_bit(available, difference);
            }
            Enumerator enumerator{options.limit, available, started + options.seconds, options.node_limit};
            std::vector<int> marks{0};
            enumerator.visit(marks, Mask{});
            nodes[omitted] = enumerator.nodes;
            complete_rows[omitted] = enumerator.complete_rows;
            compatible_rows[omitted] = enumerator.compatible_rows;
            stopped = enumerator.stopped;
            if (enumerator.found) found_rows.push_back(enumerator.candidate);
        }

        const double elapsed = clock_seconds() - started;
        std::ofstream artifact(options.output);
        artifact << "{\"method\":\"exhaustive-global-one-row-replacement\",\"status\":\"completed\",\"limit\":" << options.limit
                  << ",\"seconds\":" << options.seconds << ",\"node_limit\":" << options.node_limit
                  << ",\"stopped\":" << (stopped ? "true" : "false")
                  << ",\"target_reached\":" << (found_rows.empty() ? "false" : "true")
                  << ",\"elapsed_seconds\":" << std::setprecision(12) << elapsed << ",\"omitted_rows_checked\":[";
        bool first = true;
        for (int omitted = 0; omitted < 7; ++omitted) {
            if (!fixed_consistent[omitted]) continue;
            if (!first) artifact << ",";
            first = false;
            artifact << omitted;
        }
        artifact << "],\"nodes_by_omitted_row\":[";
        for (std::size_t index = 0; index < nodes.size(); ++index) {
            if (index) artifact << ",";
            artifact << nodes[index];
        }
        artifact << "],\"complete_rows_by_omitted_row\":[";
        for (std::size_t index = 0; index < complete_rows.size(); ++index) {
            if (index) artifact << ",";
            artifact << complete_rows[index];
        }
        artifact << "],\"compatible_rows_by_omitted_row\":[";
        for (std::size_t index = 0; index < compatible_rows.size(); ++index) {
            if (index) artifact << ",";
            artifact << compatible_rows[index];
        }
        artifact << "],\"rows\":[";
        if (!found_rows.empty()) write_row(artifact, found_rows.front());
        artifact << "]}\n";

        std::ofstream raw(options.raw);
        raw << "Experiment dts-one-row-replacement-001 execution record\n"
            << "Method: exhaustive increasing-mark enumeration of every scope-111 row compatible with six clamped published rows\n"
            << "Rows omitted and fixed-six consistency: ";
        for (int omitted = 0; omitted < 7; ++omitted) {
            raw << omitted << "=" << (fixed_consistent[omitted] ? "consistent" : "inconsistent") << " ";
        }
        raw << "\nNodes by omitted row: ";
        for (std::size_t index = 0; index < nodes.size(); ++index) raw << (index ? "," : "") << nodes[index];
        raw << "\nComplete compatible rows by omitted row: ";
        for (std::size_t index = 0; index < complete_rows.size(); ++index) raw << (index ? "," : "") << complete_rows[index];
        raw << "\nTarget reached: " << (found_rows.empty() ? "false" : "true") << "\nRows: ";
        if (!found_rows.empty()) write_row(raw, found_rows.front());
        raw << "\nElapsed seconds: " << std::setprecision(12) << elapsed << "\n";
        std::cout << "target=" << (found_rows.empty() ? "false" : "true") << " stopped=" << (stopped ? "true" : "false")
                  << " elapsed=" << elapsed << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
