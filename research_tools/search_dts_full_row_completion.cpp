#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr int kRows = 7;
constexpr int kMarks = 6;
constexpr int kLimit = 111;
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

struct Search {
    std::array<int, kLimit + 1> fixed_counts{};
    std::array<int, kLimit + 1> row_counts{};
    std::vector<int> marks{0};
    std::uint64_t nodes = 0;
    std::uint64_t complete_rows = 0;
    Row candidate{};
    bool found = false;

    void visit() {
        ++nodes;
        if (marks.size() == kMarks) {
            ++complete_rows;
            for (int index = 0; index < kMarks; ++index) candidate[index] = marks[index];
            found = true;
            return;
        }
        for (int value = marks.back() + 1; value <= kLimit && !found; ++value) {
            bool valid = true;
            for (int old : marks) {
                const int difference = value - old;
                if (fixed_counts[difference] != 0 || row_counts[difference] != 0) {
                    valid = false;
                    break;
                }
            }
            if (!valid) continue;
            marks.push_back(value);
            const int mark_index = static_cast<int>(marks.size()) - 1;
            for (int old : marks) {
                if (old == value) continue;
                ++row_counts[value - old];
            }
            visit();
            for (int old : marks) {
                if (old == value) continue;
                --row_counts[value - old];
            }
            marks.pop_back();
            (void)mark_index;
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
    if (argc != 2) {
        std::cerr << "usage: search_dts_full_row_completion OUTPUT\n";
        return 2;
    }
    Search search;
    for (int row_index = 1; row_index < kRows; ++row_index) {
        const Row& row = kBase[row_index];
        for (int right = 1; right < kMarks; ++right) {
            for (int left = 0; left < right; ++left) ++search.fixed_counts[row[right] - row[left]];
        }
    }
    int fixed_unique = 0;
    std::vector<int> allowed;
    for (int difference = 1; difference <= kLimit; ++difference) {
        if (search.fixed_counts[difference] != 0) ++fixed_unique;
        else allowed.push_back(difference);
    }
    search.visit();

    std::ofstream output(argv[1]);
    if (!output) return 3;
    output << "{\n"
           << "  \"method\":\"exact-full-row-completion-against-six-compatible-rows\",\n"
           << "  \"scope_limit\":111,\n"
           << "  \"fixed_row_count\":6,\n"
           << "  \"fixed_unique_differences\":" << fixed_unique << ",\n"
           << "  \"allowed_difference_count\":" << allowed.size() << ",\n"
           << "  \"allowed_differences\":[";
    for (std::size_t index = 0; index < allowed.size(); ++index) {
        if (index != 0) output << ',';
        output << allowed[index];
    }
    output << "],\n  \"nodes\":" << search.nodes
           << ",\n  \"complete_rows\":" << search.complete_rows
           << ",\n  \"candidate_row\":";
    write_row(output, search.candidate);
    output << ",\n  \"target_reached\":" << (search.found ? "true" : "false") << "\n}\n";
    std::cout << "fixed_unique=" << fixed_unique
              << " allowed=" << allowed.size()
              << " nodes=" << search.nodes
              << " complete_rows=" << search.complete_rows
              << " target_reached=" << (search.found ? "true" : "false") << '\n';
    return 0;
}
