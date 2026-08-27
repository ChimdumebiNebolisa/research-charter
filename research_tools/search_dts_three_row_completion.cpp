#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

constexpr int kRows = 7;
constexpr int kMarks = 6;
constexpr int kLimit = 111;
constexpr int kRowsToComplete = 3;
constexpr int kRowDifferences = 15;

struct Mask {
    std::uint64_t low = 0;
    std::uint64_t high = 0;
};

struct RowRecord {
    Mask mask;
    std::array<int, kMarks> marks{};
};

using Row = std::array<int, kMarks>;
using Rows = std::array<Row, kRows>;

const Rows kBase = {{
    Row{0, 11, 21, 58, 75, 98},
    Row{0, 12, 32, 50, 103, 111},
    Row{0, 22, 41, 89, 104, 110},
    Row{0, 28, 52, 83, 108, 109},
    Row{0, 13, 62, 72, 105, 107},
    Row{0, 9, 16, 60, 102, 106},
    Row{0, 27, 30, 66, 95, 100},
}};

double now_seconds() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

bool has_bit(const Mask& mask, int difference) {
    if (difference < 64) return (mask.low & (1ULL << difference)) != 0;
    return (mask.high & (1ULL << (difference - 64))) != 0;
}

void set_bit(Mask& mask, int difference) {
    if (difference < 64) mask.low |= 1ULL << difference;
    else mask.high |= 1ULL << (difference - 64);
}

bool overlaps(const Mask& left, const Mask& right) {
    return (left.low & right.low) != 0 || (left.high & right.high) != 0;
}

Mask row_mask(const Row& row) {
    Mask mask;
    for (int right = 1; right < kMarks; ++right) {
        for (int left = 0; left < right; ++left) set_bit(mask, row[right] - row[left]);
    }
    return mask;
}

struct Generator {
    const Mask& fixed_mask;
    double deadline;
    std::vector<RowRecord>& catalog;
    std::vector<int> marks{0};
    Mask current_mask;
    std::uint64_t nodes = 0;
    bool timed_out = false;

    void visit() {
        if (now_seconds() >= deadline) {
            timed_out = true;
            return;
        }
        ++nodes;
        if (marks.size() == kMarks) {
            RowRecord record;
            for (int index = 0; index < kMarks; ++index) record.marks[index] = marks[index];
            record.mask = current_mask;
            catalog.push_back(record);
            return;
        }
        for (int value = marks.back() + 1; value <= kLimit && !timed_out; ++value) {
            Mask next_mask = current_mask;
            bool valid = true;
            for (int old : marks) {
                const int difference = value - old;
                if (has_bit(fixed_mask, difference) || has_bit(next_mask, difference)) {
                    valid = false;
                    break;
                }
                set_bit(next_mask, difference);
            }
            if (!valid) continue;
            marks.push_back(value);
            const Mask saved = current_mask;
            current_mask = next_mask;
            visit();
            current_mask = saved;
            marks.pop_back();
        }
    }
};

struct PackingSearch {
    const std::vector<RowRecord>& catalog;
    const std::array<std::vector<int>, kLimit + 1>& by_difference;
    double deadline;
    std::uint64_t nodes = 0;
    int best_depth = 0;
    int best_gaps = 0;
    bool timed_out = false;
    bool found = false;
    std::array<int, kRowsToComplete> selected{};
    std::array<int, kRowsToComplete> best_selected{};

    int compatible_count(int difference, const Mask& used) const {
        int count = 0;
        for (int index : by_difference[difference]) {
            if (!overlaps(catalog[index].mask, used)) ++count;
        }
        return count;
    }

    void search(const Mask& used, int depth, int gaps, const Mask& gap_mask) {
        if (found || timed_out) return;
        if (now_seconds() >= deadline) {
            timed_out = true;
            return;
        }
        ++nodes;
        if (depth > best_depth || (depth == best_depth && gaps > best_gaps)) {
            best_depth = depth;
            best_gaps = gaps;
            best_selected = selected;
        }
        if (depth == kRowsToComplete) {
            found = true;
            best_selected = selected;
            return;
        }
        int remaining_available = 0;
        int anchor = 0;
        int anchor_count = std::numeric_limits<int>::max();
        for (int difference = 1; difference <= kLimit; ++difference) {
            if (has_bit(used, difference) || has_bit(gap_mask, difference)) continue;
            ++remaining_available;
            const int count = compatible_count(difference, used);
            if (count < anchor_count) {
                anchor_count = count;
                anchor = difference;
            }
        }
        if (remaining_available < (kRowsToComplete - depth) * kRowDifferences) return;
        if (anchor == 0) return;

        for (int index : by_difference[anchor]) {
            if (overlaps(catalog[index].mask, used)) continue;
            selected[depth] = index;
            search(Mask{used.low | catalog[index].mask.low, used.high | catalog[index].mask.high}, depth + 1, gaps, gap_mask);
            if (found || timed_out) return;
        }
        if (gaps < 6) {
            Mask next_gaps = gap_mask;
            set_bit(next_gaps, anchor);
            search(used, depth, gaps + 1, next_gaps);
        }
    }
};

void write_row(std::ostream& output, const Row& row) {
    output << '[';
    for (int index = 0; index < kMarks; ++index) {
        if (index != 0) output << ',';
        output << row[index];
    }
    output << ']';
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: search_dts_three_row_completion SECONDS OUTPUT\n";
        return 2;
    }
    const double seconds = std::stod(argv[1]);
    const double deadline = now_seconds() + seconds;

    Mask fixed_mask;
    for (int row_index : {1, 3, 5, 6}) {
        const Mask mask = row_mask(kBase[row_index]);
        fixed_mask.low |= mask.low;
        fixed_mask.high |= mask.high;
    }
    std::vector<RowRecord> catalog;
    catalog.reserve(1000000);
    Generator generator{fixed_mask, deadline, catalog};
    generator.visit();

    std::array<std::vector<int>, kLimit + 1> by_difference;
    for (std::size_t index = 0; index < catalog.size(); ++index) {
        for (int difference = 1; difference <= kLimit; ++difference) {
            if (has_bit(catalog[index].mask, difference)) by_difference[difference].push_back(static_cast<int>(index));
        }
    }
    PackingSearch packing{catalog, by_difference, deadline};
    if (!generator.timed_out) packing.search(fixed_mask, 0, 0, Mask{});

    int fixed_unique = 0;
    for (int difference = 1; difference <= kLimit; ++difference) if (has_bit(fixed_mask, difference)) ++fixed_unique;
    std::ofstream output(argv[2]);
    if (!output) return 3;
    output << "{\n"
           << "  \"method\":\"exact-three-row-packing-against-four-compatible-rows\",\n"
           << "  \"scope_limit\":111,\n"
           << "  \"fixed_row_count\":4,\n"
           << "  \"fixed_unique_differences\":" << fixed_unique << ",\n"
           << "  \"catalog_size\":" << catalog.size() << ",\n"
           << "  \"generation_nodes\":" << generator.nodes << ",\n"
           << "  \"generation_timed_out\":" << (generator.timed_out ? "true" : "false") << ",\n"
           << "  \"packing_nodes\":" << packing.nodes << ",\n"
           << "  \"packing_timed_out\":" << (packing.timed_out ? "true" : "false") << ",\n"
           << "  \"best_depth\":" << packing.best_depth << ",\n"
           << "  \"best_gaps\":" << packing.best_gaps << ",\n"
           << "  \"target_reached\":" << (packing.found ? "true" : "false") << ",\n"
           << "  \"rows\":[";
    bool first = true;
    for (int row_index : {1, 3, 5, 6}) {
        if (!first) output << ',';
        first = false;
        write_row(output, kBase[row_index]);
    }
    if (packing.found) {
        for (int index : packing.selected) {
            output << ',';
            write_row(output, catalog[index].marks);
        }
    }
    output << "]\n}\n";
    std::cout << "catalog=" << catalog.size()
              << " generation_nodes=" << generator.nodes
              << " packing_nodes=" << packing.nodes
              << " best_depth=" << packing.best_depth
              << " best_gaps=" << packing.best_gaps
              << " target_reached=" << (packing.found ? "true" : "false") << '\n';
    return 0;
}
