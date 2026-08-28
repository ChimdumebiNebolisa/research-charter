// Capability benchmark for exact disjoint-mask packing over a complete catalogue.
// This intentionally measures shallow scans only; it does not launch depth seven.

#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Header {
    std::uint32_t magic;
    std::uint32_t version;
    std::uint32_t scope_limit;
    std::uint32_t record_size;
    std::uint64_t count;
};

struct Row {
    std::uint8_t marks[6];
    std::uint8_t scope;
    std::uint8_t reserved[1];
    std::uint64_t lo;
    std::uint64_t hi;
};

static bool disjoint(const Row& left, const Row& right) {
    return (left.lo & right.lo) == 0 && (left.hi & right.hi) == 0;
}

static std::vector<Row> read_catalogue(const std::string& path, Header& header) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open catalogue");
    input.read(reinterpret_cast<char*>(&header), sizeof(header));
    if (!input || header.magic != 0x44545352 || header.version != 1 || header.record_size != sizeof(Row)) throw std::runtime_error("invalid catalogue header");
    std::vector<Row> rows(static_cast<std::size_t>(header.count));
    input.read(reinterpret_cast<char*>(rows.data()), static_cast<std::streamsize>(rows.size() * sizeof(Row)));
    if (!input) throw std::runtime_error("short catalogue");
    return rows;
}

struct ScanResult {
    std::uint64_t compatible = 0;
    std::uint64_t first_index = UINT64_MAX;
    double seconds = 0;
};

static ScanResult scan_compatible(const std::vector<Row>& rows, const Row& used, std::size_t start) {
    const auto started = std::chrono::steady_clock::now();
    ScanResult result;
    for (std::size_t index = start; index < rows.size(); ++index) {
        if (disjoint(used, rows[index])) {
            ++result.compatible;
            if (result.first_index == UINT64_MAX) result.first_index = index;
        }
    }
    result.seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
    return result;
}

static std::uint64_t count_compatible(const std::vector<Row>& rows, const Row& first, const Row& second, std::size_t start, double& seconds) {
    const auto started = std::chrono::steady_clock::now();
    std::uint64_t count = 0;
    const std::uint64_t used_lo = first.lo | second.lo;
    const std::uint64_t used_hi = first.hi | second.hi;
    for (std::size_t index = start; index < rows.size(); ++index) {
        if ((used_lo & rows[index].lo) == 0 && (used_hi & rows[index].hi) == 0) ++count;
    }
    seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
    return count;
}

static std::size_t first_compatible_pair(const std::vector<Row>& rows, const Row& first, const Row& second, std::size_t start) {
    const std::uint64_t used_lo = first.lo | second.lo;
    const std::uint64_t used_hi = first.hi | second.hi;
    for (std::size_t index = start; index < rows.size(); ++index) {
        if ((used_lo & rows[index].lo) == 0 && (used_hi & rows[index].hi) == 0) return index;
    }
    return UINT64_MAX;
}

static std::uint64_t count_compatible4(const std::vector<Row>& rows, const Row& first, const Row& second, const Row& third, std::size_t start, double& seconds) {
    const auto started = std::chrono::steady_clock::now();
    const std::uint64_t used_lo = first.lo | second.lo | third.lo;
    const std::uint64_t used_hi = first.hi | second.hi | third.hi;
    std::uint64_t count = 0;
    for (std::size_t index = start; index < rows.size(); ++index) {
        if ((used_lo & rows[index].lo) == 0 && (used_hi & rows[index].hi) == 0) ++count;
    }
    seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
    return count;
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: benchmark_dts_packing CATALOGUE");
        Header header{};
        auto rows = read_catalogue(argv[1], header);
        std::cout << std::setprecision(12);
        std::cout << "{\"catalogue_rows\":" << rows.size() << ",\"scope_limit\":" << header.scope_limit << ",\"depth2\":[";
        for (int sample = 0; sample < 8; ++sample) {
            const std::size_t first = static_cast<std::size_t>((static_cast<std::uint64_t>(sample) * rows.size()) / 8);
            const auto result = scan_compatible(rows, rows[first], first + 1);
            if (sample) std::cout << ",";
            std::cout << "{\"first_index\":" << first << ",\"compatible_second_rows\":" << result.compatible << ",\"first_scan_seconds\":" << result.seconds << ",\"rows_per_second\":" << (rows.size() / result.seconds) << ",\"first_second_index\":" << result.first_index << "}";
        }
        std::cout << "],\"depth3\":[";
        for (int sample = 0; sample < 4; ++sample) {
            const std::size_t first = static_cast<std::size_t>((static_cast<std::uint64_t>(sample) * rows.size()) / 4);
            const auto second_scan = scan_compatible(rows, rows[first], first + 1);
            if (second_scan.first_index == UINT64_MAX) throw std::runtime_error("no representative compatible second row");
            double seconds = 0;
            const auto count = count_compatible(rows, rows[first], rows[second_scan.first_index], second_scan.first_index + 1, seconds);
            if (sample) std::cout << ",";
            std::cout << "{\"first_index\":" << first << ",\"second_index\":" << second_scan.first_index << ",\"compatible_third_rows\":" << count << ",\"scan_seconds\":" << seconds << ",\"rows_per_second\":" << (rows.size() / seconds) << "}";
        }
        std::cout << "],\"depth4\":[";
        const std::size_t depth4_first[] = {19696868, 39393737};
        const std::size_t depth4_second[] = {22613753, 39646846};
        for (int sample = 0; sample < 2; ++sample) {
            const std::size_t first = depth4_first[sample];
            const std::size_t second = depth4_second[sample];
            if (!disjoint(rows[first], rows[second])) throw std::runtime_error("invalid representative compatible pair");
            double depth3_seconds = 0;
            const auto third_index = first_compatible_pair(rows, rows[first], rows[second], second + 1);
            if (third_index == UINT64_MAX) throw std::runtime_error("no representative compatible third row");
            const auto third_count = count_compatible(rows, rows[first], rows[second], second + 1, depth3_seconds);
            double seconds = 0;
            const auto count = count_compatible4(rows, rows[first], rows[second], rows[third_index], third_index + 1, seconds);
            if (sample) std::cout << ",";
            std::cout << "{\"first_index\":" << first << ",\"second_index\":" << second << ",\"third_index\":" << third_index << ",\"compatible_fourth_rows\":" << count << ",\"scan_seconds\":" << seconds << ",\"rows_per_second\":" << (rows.size() / seconds) << ",\"depth3_probe_count\":" << third_count << "}";
        }
        std::cout << "]}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
