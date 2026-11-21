// Fuzz targets for what the layer parses from files a user, the panel or an
// earlier run wrote: the configuration (and the shipped profiles), the
// status files the panel and --report read, options_ui.conf, the
// online_tune cache. One target per build (CHUDS_FG_FUZZ_TARGET):
//   config | status | options_ui | online_tune
// Built with -fsanitize=fuzzer (CHUDS_FG_FUZZ=ON, Clang: tools/ci/fuzz.sh), or
// with the replay driver below (every build: ctest fuzz_replay runs the
// seed corpus and the inputs that once failed, tests/fuzz/corpus/<target>).
// Beyond not crashing, each checks a property: options within their
// declared ranges, a cache that reads back to itself.
#include "config.h"
#include "log.h"
#include "online_tune.h"
#include "options_ui.h"
#include "status.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

#ifndef CHUDS_FG_FUZZ_TARGET
#error "CHUDS_FG_FUZZ_TARGET must name the target"
#endif

namespace {

void fail(const char* what, const std::string& detail) {
    fprintf(stderr, "fuzz: %s: %s\n", what, detail.c_str());
    abort();
}

void fuzzConfig(const std::string& text) {
    // As the user's file, then as a shipped profiles file, for a process
    // its sections may name.
    for (bool bundled : {false, true}) {
        chuds_fg::Config c;
        std::istringstream in(text);
        c.loadStream(in, "fuzz", "game.exe", bundled);
        const std::string bad = c.outOfBounds();
        if (!bad.empty()) fail("option out of range", bad);
        if (bundled && c.enabled != chuds_fg::Config{}.enabled) fail("a profile turned the layer on", "enabled");
        (void)c.describe();
        (void)c.tuneCandidates();
        (void)c.sameOutputSettings(chuds_fg::Config{});
        chuds_fg::Config live;
        live.applyLive(c);
        if (!live.outOfBounds().empty()) fail("live reload out of range", live.outOfBounds());
    }
    // Every line as key = value, as the environment would give it.
    chuds_fg::Config e;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        const size_t eq = line.find('=');
        if (eq != std::string::npos) e.apply(line.substr(0, eq), line.substr(eq + 1));
        else e.applyPreset(line);
    }
    if (!e.outOfBounds().empty()) fail("option out of range (apply)", e.outOfBounds());
}

void fuzzStatus(const std::string& text) {
    const chuds_fg::StatusFile f = chuds_fg::statusParse(text);
    for (const std::string& line : chuds_fg::statusDescribe(f)) (void)line.size();
}

void fuzzOptionsUi(const std::string& text) {
    std::vector<std::string> errors;
    (void)chuds_fg::parseOptionsUi(text, errors);
}

void fuzzOnlineTune(const std::string& text) {
    for (bool extrapolate : {false, true}) {
        chuds_fg::Config c;
        c.extrapolate = extrapolate;
        std::vector<chuds_fg::OnlineTune::Candidate> cands;
        for (const auto& t : c.tuneCandidates()) cands.push_back({t.key, t.value, t.synthesis});
        chuds_fg::OnlineTune a(cands);
        if (!a.deserialize(text)) continue;
        // What a cache reads back to is what it is written again as.
        const std::string once = a.serialize();
        chuds_fg::OnlineTune b(cands);
        b.deserialize(once);
        if (b.serialize() != once) fail("online_tune cache does not read back to itself", once);
        (void)a.summary();
    }
}

} // namespace

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    chuds_fg::log_set_level(-1);  // (the warnings on every ignored option)
    const std::string text(reinterpret_cast<const char*>(data), size);
    const std::string target = CHUDS_FG_FUZZ_TARGET;
    if (target == "config") fuzzConfig(text);
    else if (target == "status") fuzzStatus(text);
    else if (target == "options_ui") fuzzOptionsUi(text);
    else if (target == "online_tune") fuzzOnlineTune(text);
    return 0;
}

#ifndef CHUDS_FG_LIBFUZZER
// The replay driver: each argument is an input file.
int main(int argc, char** argv) {
    int n = 0;
    for (int i = 1; i < argc; ++i) {
        FILE* f = fopen(argv[i], "rb");
        if (!f) { fprintf(stderr, "cannot read %s\n", argv[i]); return 1; }
        std::string data;
        char buf[4096];
        for (size_t r; (r = fread(buf, 1, sizeof buf, f)) > 0;) data.append(buf, r);
        fclose(f);
        LLVMFuzzerTestOneInput(reinterpret_cast<const uint8_t*>(data.data()), data.size());
        ++n;
    }
    printf("%s: %d input(s) replayed\n", CHUDS_FG_FUZZ_TARGET, n);
    return 0;
}
#endif
