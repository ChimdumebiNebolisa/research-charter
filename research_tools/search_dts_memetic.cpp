#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <string>
#include <vector>

namespace {

constexpr int kRows = 7;
constexpr int kMarks = 6;
constexpr int kDifferencesPerRow = 15;
constexpr int kLimit = 111;

using Row = std::array<int, kMarks>;
using Chromosome = std::array<Row, kRows>;

struct Evaluation {
    int unique = 0;
    int internal_invalid = 0;
};

struct Individual {
    Chromosome rows{};
    Evaluation evaluation{};
};

double now_seconds() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

bool row_valid(const Row& row) {
    if (row[0] != 0) return false;
    for (int i = 1; i < kMarks; ++i) {
        if (row[i] <= row[i - 1] || row[i] > kLimit) return false;
    }
    std::array<int, kLimit + 1> seen{};
    for (int right = 1; right < kMarks; ++right) {
        for (int left = 0; left < right; ++left) {
            const int difference = row[right] - row[left];
            if (difference < 1 || difference > kLimit || seen[difference] != 0) return false;
            seen[difference] = 1;
        }
    }
    return true;
}

Evaluation evaluate(const Chromosome& rows) {
    std::array<int, kLimit + 1> counts{};
    Evaluation result;
    for (const Row& row : rows) {
        if (!row_valid(row)) {
            ++result.internal_invalid;
            continue;
        }
        for (int right = 1; right < kMarks; ++right) {
            for (int left = 0; left < right; ++left) {
                ++counts[row[right] - row[left]];
            }
        }
    }
    for (int difference = 1; difference <= kLimit; ++difference) {
        if (counts[difference] != 0) ++result.unique;
    }
    return result;
}

bool better(const Evaluation& left, const Evaluation& right) {
    if (left.internal_invalid != right.internal_invalid) return left.internal_invalid < right.internal_invalid;
    return left.unique > right.unique;
}

Row random_row(std::mt19937_64& rng) {
    std::uniform_int_distribution<int> value(1, kLimit);
    Row row{};
    while (true) {
        row[0] = 0;
        for (int i = 1; i < kMarks; ++i) row[i] = value(rng);
        std::sort(row.begin() + 1, row.end());
        if (row_valid(row)) return row;
    }
}

const std::array<Row, kRows> kClampedBaseline = {{
    Row{0, 11, 58, 75, 98, 111},
    Row{0, 12, 32, 50, 103, 111},
    Row{0, 22, 41, 89, 104, 110},
    Row{0, 28, 52, 83, 108, 109},
    Row{0, 13, 62, 72, 105, 107},
    Row{0, 9, 16, 60, 102, 106},
    Row{0, 27, 30, 66, 95, 100},
}};

Individual make_random_individual(std::mt19937_64& rng) {
    Individual individual;
    for (Row& row : individual.rows) row = random_row(rng);
    individual.evaluation = evaluate(individual.rows);
    return individual;
}

void collect_conflict_rows(const Chromosome& rows, std::vector<int>& conflict_rows, std::array<int, kLimit + 1>& missing) {
    std::array<int, kLimit + 1> counts{};
    for (const Row& row : rows) {
        if (!row_valid(row)) continue;
        for (int right = 1; right < kMarks; ++right) {
            for (int left = 0; left < right; ++left) ++counts[row[right] - row[left]];
        }
    }
    conflict_rows.clear();
    for (int difference = 1; difference <= kLimit; ++difference) {
        missing[difference] = counts[difference] == 0 ? 1 : 0;
    }
    for (int row_index = 0; row_index < kRows; ++row_index) {
        bool conflict = false;
        for (int right = 1; right < kMarks && !conflict; ++right) {
            for (int left = 0; left < right; ++left) {
                const int difference = rows[row_index][right] - rows[row_index][left];
                if (difference >= 1 && difference <= kLimit && counts[difference] > 1) {
                    conflict = true;
                    break;
                }
            }
        }
        if (conflict) conflict_rows.push_back(row_index);
    }
}

Row propose_row(const Row& original, const std::array<int, kLimit + 1>& missing, std::mt19937_64& rng) {
    Row candidate = original;
    std::uniform_int_distribution<int> mark_index(1, kMarks - 1);
    std::uniform_int_distribution<int> value(1, kLimit);
    const int index = mark_index(rng);
    int proposed = value(rng);
    if ((rng() & 1ULL) == 0) {
        std::vector<int> missing_values;
        for (int difference = 1; difference <= kLimit; ++difference) {
            if (missing[difference] != 0) missing_values.push_back(difference);
        }
        if (!missing_values.empty()) {
            const int difference = missing_values[static_cast<std::size_t>(rng() % missing_values.size())];
            const int anchor_index = static_cast<int>(rng() % kMarks);
            const int sign = (rng() & 1ULL) == 0 ? 1 : -1;
            proposed = original[anchor_index] + sign * difference;
        }
    }
    candidate[index] = std::max(1, std::min(kLimit, proposed));
    std::sort(candidate.begin() + 1, candidate.end());
    candidate[0] = 0;
    return candidate;
}

void polish(Individual& individual, std::mt19937_64& rng, int steps) {
    std::vector<int> conflict_rows;
    std::array<int, kLimit + 1> missing{};
    for (int step = 0; step < steps; ++step) {
        collect_conflict_rows(individual.rows, conflict_rows, missing);
        int row_index;
        if (!conflict_rows.empty() && (rng() % 100ULL) < 85ULL) {
            row_index = conflict_rows[static_cast<std::size_t>(rng() % conflict_rows.size())];
        } else {
            row_index = static_cast<int>(rng() % kRows);
        }
        Individual candidate = individual;
        candidate.rows[row_index] = propose_row(candidate.rows[row_index], missing, rng);
        candidate.evaluation = evaluate(candidate.rows);
        if (better(candidate.evaluation, individual.evaluation)) {
            individual = candidate;
        } else if (candidate.evaluation.internal_invalid == individual.evaluation.internal_invalid &&
                   candidate.evaluation.unique == individual.evaluation.unique && (rng() % 100ULL) < 7ULL) {
            individual = candidate;
        }
    }
}

Individual crossover(const Individual& first, const Individual& second, std::mt19937_64& rng) {
    Individual child;
    for (int row_index = 0; row_index < kRows; ++row_index) {
        child.rows[row_index] = ((rng() & 1ULL) == 0) ? first.rows[row_index] : second.rows[row_index];
    }
    child.evaluation = evaluate(child.rows);
    return child;
}

int tournament(const std::vector<Individual>& population, std::mt19937_64& rng) {
    int best_index = static_cast<int>(rng() % population.size());
    for (int trial = 0; trial < 3; ++trial) {
        const int candidate = static_cast<int>(rng() % population.size());
        if (better(population[candidate].evaluation, population[best_index].evaluation)) best_index = candidate;
    }
    return best_index;
}

void write_row(std::ostream& output, const Row& row) {
    output << '[';
    for (int index = 0; index < kMarks; ++index) {
        if (index != 0) output << ',';
        output << row[index];
    }
    output << ']';
}

void write_individual(std::ostream& output, const Individual& individual) {
    output << '[';
    for (int row_index = 0; row_index < kRows; ++row_index) {
        if (row_index != 0) output << ',';
        write_row(output, individual.rows[row_index]);
    }
    output << ']';
}

struct RunResult {
    std::uint64_t seed = 0;
    std::uint64_t iterations = 0;
    std::uint64_t replacements = 0;
    std::uint64_t best_updates = 0;
    double elapsed_seconds = 0.0;
    Individual best{};
};

RunResult run(std::uint64_t seed, double seconds, int population_size, int polish_steps) {
    const double started = now_seconds();
    std::mt19937_64 rng(seed);
    std::vector<Individual> population;
    population.reserve(static_cast<std::size_t>(population_size));

    Individual baseline;
    baseline.rows = kClampedBaseline;
    baseline.evaluation = evaluate(baseline.rows);
    population.push_back(baseline);
    while (static_cast<int>(population.size()) < population_size) {
        Individual individual = make_random_individual(rng);
        if ((rng() % 100ULL) < 20ULL) polish(individual, rng, polish_steps / 2);
        population.push_back(individual);
    }
    const double search_deadline = now_seconds() + seconds;

    Individual best = population.front();
    for (const Individual& individual : population) {
        if (better(individual.evaluation, best.evaluation)) best = individual;
    }

    std::uint64_t iterations = 0;
    std::uint64_t replacements = 0;
    std::uint64_t best_updates = 0;
    while (now_seconds() < search_deadline) {
        ++iterations;
        const int first_index = tournament(population, rng);
        const int second_index = tournament(population, rng);
        Individual child = crossover(population[first_index], population[second_index], rng);
        if ((rng() % 100ULL) < 35ULL) {
            const int row_index = static_cast<int>(rng() % kRows);
            child.rows[row_index] = random_row(rng);
            child.evaluation = evaluate(child.rows);
        }
        polish(child, rng, polish_steps);
        if (better(child.evaluation, best.evaluation)) {
            best = child;
            ++best_updates;
        }
        int worst_index = 0;
        for (int index = 1; index < population_size; ++index) {
            if (better(population[worst_index].evaluation, population[index].evaluation)) worst_index = index;
        }
        if (better(child.evaluation, population[worst_index].evaluation) ||
            (child.evaluation.unique == population[worst_index].evaluation.unique &&
             child.evaluation.internal_invalid == population[worst_index].evaluation.internal_invalid &&
             (rng() % 100ULL) < 3ULL)) {
            population[worst_index] = child;
            ++replacements;
        }
        if (best.evaluation.internal_invalid == 0 && best.evaluation.unique == kRows * kDifferencesPerRow) break;
    }
    return RunResult{seed, iterations, replacements, best_updates, now_seconds() - started, best};
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: search_dts_memetic SECONDS_PER_SEED POPULATION POLISH_STEPS OUTPUT\n";
        return 2;
    }
    const double seconds_per_seed = std::stod(argv[1]);
    const int population_size = std::stoi(argv[2]);
    const int polish_steps = std::stoi(argv[3]);
    const std::string output_path = argv[4];
    const std::array<std::uint64_t, 3> seeds = {20260828ULL, 20260829ULL, 20260830ULL};

    std::ofstream output(output_path);
    if (!output) {
        std::cerr << "cannot open output: " << output_path << '\n';
        return 3;
    }
    output << "{\n  \"method\":\"memetic-row-crossover-conflict-directed-coordinate-repair\",\n"
           << "  \"scope_limit\":111,\n  \"population_size\":" << population_size
           << ",\n  \"polish_steps\":" << polish_steps
           << ",\n  \"seconds_per_seed\":" << std::setprecision(17) << seconds_per_seed
           << ",\n  \"runs\":[\n";

    bool target_reached = false;
    for (std::size_t run_index = 0; run_index < seeds.size(); ++run_index) {
        const RunResult result = run(seeds[run_index], seconds_per_seed, population_size, polish_steps);
        target_reached = target_reached ||
            (result.best.evaluation.internal_invalid == 0 && result.best.evaluation.unique == kRows * kDifferencesPerRow);
        output << "    {\n      \"seed\":" << result.seed
               << ",\n      \"iterations\":" << result.iterations
               << ",\n      \"replacements\":" << result.replacements
               << ",\n      \"best_updates\":" << result.best_updates
               << ",\n      \"elapsed_seconds\":" << std::setprecision(17) << result.elapsed_seconds
               << ",\n      \"best_unique\":" << result.best.evaluation.unique
               << ",\n      \"best_internal_invalid\":" << result.best.evaluation.internal_invalid
               << ",\n      \"best_rows\":";
        write_individual(output, result.best);
        output << "\n    }" << (run_index + 1 == seeds.size() ? "\n" : ",\n");
        std::cout << "seed=" << result.seed << " best_unique=" << result.best.evaluation.unique
                  << " iterations=" << result.iterations << " elapsed=" << result.elapsed_seconds << '\n';
        if (target_reached) break;
    }
    output << "  ],\n  \"target_reached\":" << (target_reached ? "true" : "false") << "\n}\n";
    return 0;
}
