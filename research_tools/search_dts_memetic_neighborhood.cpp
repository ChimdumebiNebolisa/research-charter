#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
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

struct Score {
    int unique = 0;
    bool internally_valid = false;
};

Score score(const Rows& rows) {
    std::array<int, kLimit + 1> counts{};
    for (const Row& row : rows) {
        if (row[0] != 0) return {};
        for (int mark = 1; mark < kMarks; ++mark) {
            if (row[mark] <= row[mark - 1] || row[mark] > kLimit) return {};
        }
        for (int right = 1; right < kMarks; ++right) {
            for (int left = 0; left < right; ++left) {
                const int difference = row[right] - row[left];
                if (difference < 1 || difference > kLimit || counts[difference] < 0) return {};
                ++counts[difference];
            }
        }
    }
    // Recheck each row separately: score()'s first pass intentionally counts
    // globally, while internal Golomb validity must be checked row by row.
    for (const Row& row : rows) {
        std::array<int, kLimit + 1> row_counts{};
        for (int right = 1; right < kMarks; ++right) {
            for (int left = 0; left < right; ++left) {
                const int difference = row[right] - row[left];
                if (++row_counts[difference] > 1) return {};
            }
        }
    }
    int unique = 0;
    for (int difference = 1; difference <= kLimit; ++difference) {
        if (counts[difference] > 0) ++unique;
    }
    return {unique, true};
}

void write_row(std::ostream& output, const Row& row) {
    output << '[';
    for (int index = 0; index < kMarks; ++index) {
        if (index != 0) output << ',';
        output << row[index];
    }
    output << ']';
}

void write_rows(std::ostream& output, const Rows& rows) {
    output << '[';
    for (int row = 0; row < kRows; ++row) {
        if (row != 0) output << ',';
        write_row(output, rows[row]);
    }
    output << ']';
}

struct Position {
    int row;
    int mark;
};

bool better(const Score& left, const Score& right) {
    if (left.internally_valid != right.internally_valid) return left.internally_valid;
    return left.unique > right.unique;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: search_dts_memetic_neighborhood OUTPUT\n";
        return 2;
    }
    std::ofstream output(argv[1]);
    if (!output) return 3;

    std::vector<Position> positions;
    for (int row = 0; row < kRows; ++row) {
        for (int mark = 1; mark < kMarks; ++mark) positions.push_back({row, mark});
    }

    Rows best_rows = kBase;
    Score best_score = score(kBase);
    std::uint64_t one_coordinate_cases = 0;
    std::uint64_t two_coordinate_cases = 0;
    std::uint64_t internally_valid_cases = 0;
    bool target_reached = false;

    auto test = [&](const Rows& rows, bool two_coordinates) {
        if (two_coordinates) ++two_coordinate_cases;
        else ++one_coordinate_cases;
        const Score current = score(rows);
        if (!current.internally_valid) return;
        ++internally_valid_cases;
        if (better(current, best_score)) best_rows = rows, best_score = current;
        if (best_score.unique == kRows * 15) target_reached = true;
    };

    for (const Position& first : positions) {
        for (int first_value = 1; first_value <= kLimit && !target_reached; ++first_value) {
            Rows candidate = kBase;
            candidate[first.row][first.mark] = first_value;
            std::sort(candidate[first.row].begin() + 1, candidate[first.row].end());
            test(candidate, false);
        }
    }

    for (std::size_t first_index = 0; first_index < positions.size() && !target_reached; ++first_index) {
        for (std::size_t second_index = first_index + 1; second_index < positions.size() && !target_reached; ++second_index) {
            const Position first = positions[first_index];
            const Position second = positions[second_index];
            for (int first_value = 1; first_value <= kLimit && !target_reached; ++first_value) {
                for (int second_value = 1; second_value <= kLimit && !target_reached; ++second_value) {
                    Rows candidate = kBase;
                    candidate[first.row][first.mark] = first_value;
                    candidate[second.row][second.mark] = second_value;
                    std::sort(candidate[first.row].begin() + 1, candidate[first.row].end());
                    if (second.row != first.row) std::sort(candidate[second.row].begin() + 1, candidate[second.row].end());
                    test(candidate, true);
                }
            }
        }
    }

    output << "{\n"
           << "  \"method\":\"exhaustive-one-and-two-coordinate-neighborhood-of-memetic-103-state\",\n"
           << "  \"scope_limit\":111,\n"
           << "  \"coordinate_count\":" << positions.size() << ",\n"
           << "  \"one_coordinate_cases\":" << one_coordinate_cases << ",\n"
           << "  \"two_coordinate_cases\":" << two_coordinate_cases << ",\n"
           << "  \"internally_valid_cases\":" << internally_valid_cases << ",\n"
           << "  \"best_unique\":" << best_score.unique << ",\n"
           << "  \"best_internal_valid\":" << (best_score.internally_valid ? "true" : "false") << ",\n"
           << "  \"best_rows\":";
    write_rows(output, best_rows);
    output << ",\n  \"target_reached\":" << (target_reached ? "true" : "false") << "\n}\n";
    std::cout << "one_coordinate_cases=" << one_coordinate_cases
              << " two_coordinate_cases=" << two_coordinate_cases
              << " internally_valid_cases=" << internally_valid_cases
              << " best_unique=" << best_score.unique
              << " target_reached=" << (target_reached ? "true" : "false") << '\n';
    return 0;
}
