"""
Operator Algebra Diagnostic Scanner
------------------------------------
Computes real, measured (r, s, f, e) values per tick from telemetry, then
matches the SIGN of the change between ticks against the fixed-sign
generators from Table 2.1 of "An Operator Algebra Over Recursion, Scale,
Flow, and Entropy" (Onion, Apple, Gate, Stack, Mirror, Funnel, Hydra, Echo,
Spiral). A match means: "this subsystem's r/s/f/e moved in exactly the
pattern that operator's narrative reading describes."

This is a labeling/diagnostic tool only. It does not alter or control the
system being scanned -- it reports which named pattern (if any) the
measured telemetry matches, each tick, the same way an antivirus scanner
reports which signature a sample matches without itself doing anything to
the sample.

WHERE THE FOUR NUMBERS ACTUALLY COME FROM (no metaphors, all measured):

    r = self_calls / total_calls
        Fraction of this component's actions that were checks against its
        own prior output rather than an external/independent source.

    s = active_units / scale_reference
        Concurrent breadth currently engaged, normalized against a
        reference ceiling you choose per-system (e.g. max threads seen).

    f = admitted_external / attempted_external
        Of the external correction/input attempts made against this
        component, how many were actually let through.

    e = 1 - normalized_entropy(recent_state_hashes)
        1 minus the Shannon-entropy diversity of the last N internal
        state snapshots. High e = the component is producing the same
        state repeatedly = distinctions are collapsing.

Each of r, s, f, e is a real number in [0, 1], computed from data you
actually have to supply (counts, hashes) -- not asserted.
"""

import math
from collections import deque, Counter

# ---------------------------------------------------------------------------
# Table 2.1 -- fixed-sign generators, taken directly from the paper.
# Starred (uncertain-magnitude) entries keep their stated sign for matching.
# ---------------------------------------------------------------------------
OPERATORS = {
    "Onion":  {"sign": (0, 0, -1, 0), "reading": "insulates a core process, blocking corrective flow from reaching it"},
    "Apple":  {"sign": (0, 1, 0, 1), "reading": "dissolves working distinctions; affected scope uncertain"},
    "Gate":   {"sign": (0, -1, 1, 0), "reading": "opens admissible corrective flow while narrowing active scope"},
    "Stack":  {"sign": (-1, 0, 1, 0), "reading": "layers independent checks, trading self-reference for open flow"},
    "Mirror": {"sign": (1, -1, 0, 0), "reading": "collapses toward self-referential confirmation; scope effect uncertain"},
    "Funnel": {"sign": (0, -1, 0, 0), "reading": "narrows engaged scale without altering flow or recursion directly"},
    "Hydra":  {"sign": (0, 1, -1, 0), "reading": "multiplies and expands across scale as flow is constrained"},
    "Echo":   {"sign": (1, 0, -1, 0), "reading": "folds toward self-reference by way of a shared upstream source"},
    "Spiral": {"sign": (0, 0, 0, -1), "reading": "revisits a prior state with distinctions sharpened rather than lost"},
}

# Human-facing category for what each operator match implies, so the report
# says "bottleneck" / "sealed" rather than just an operator's proper name.
CATEGORY = {
    "Onion":  "SEALED (flow blocked, nothing else moving)",
    "Gate":   "OPENING (flow increasing, scope narrowing)",
    "Stack":  "DECOUPLING (dropping self-reference in favor of external checks)",
    "Mirror": "SELF-REFERENCE RISING (turning inward, away from external checks)",
    "Echo":   "SELF-REFERENCE VIA SHARED SOURCE (folding back through one upstream feed)",
    "Funnel": "NARROWING (scope shrinking, nothing else changing)",
    "Hydra":  "BOTTLENECK (scale expanding while flow is constrained)",
    "Apple":  "DISTINCTION LOSS SPREADING (entropy up, scope effect unclear)",
    "Spiral": "ENTROPY IMPROVING (repeats prior state but sharper, not blurrier)",
}


class OperatorScanner:
    def __init__(self, scale_reference=10, state_window=8, epsilon=0.02):
        self.scale_reference = scale_reference
        self.state_window = state_window
        self.epsilon = epsilon  # minimum change to count as + or - rather than 0
        self.recent_states = deque(maxlen=state_window)
        self.prev_rsfe = None
        self.tick_index = 0
        self.window_full_since_tick = None
        self.log = []

    def _entropy_component(self, state_snapshot):
        self.recent_states.append(state_snapshot)
        n = len(self.recent_states)
        if n < 2:
            return 0.0
        counts = Counter(self.recent_states)
        probs = [c / n for c in counts.values()]
        h = -sum(p * math.log2(p) for p in probs)
        h_max = math.log2(n)
        diversity = h / h_max if h_max > 0 else 1.0
        return 1.0 - diversity  # e: high = distinctions collapsing

    def measure(self, self_calls, total_calls, active_units,
                admitted_external, attempted_external, state_snapshot):
        r = self_calls / total_calls if total_calls else 0.0
        s = min(1.0, active_units / self.scale_reference)
        f = admitted_external / attempted_external if attempted_external else 1.0
        e = self._entropy_component(state_snapshot)
        return (r, s, f, e)

    def _sign(self, delta):
        if delta > self.epsilon:
            return 1
        if delta < -self.epsilon:
            return -1
        return 0

    def _match(self, sign_vec):
        if sign_vec == (0, 0, 0, 0):
            return None, 0
        best_name, best_score = None, -1
        for name, spec in OPERATORS.items():
            score = sum(1 for a, b in zip(sign_vec, spec["sign"]) if a == b)
            # require at least one non-zero axis to actually agree,
            # not just agreeing on the zeros
            nonzero_agree = sum(
                1 for a, b in zip(sign_vec, spec["sign"]) if a == b and a != 0
            )
            if nonzero_agree == 0:
                continue
            if score > best_score:
                best_name, best_score = name, score
        return best_name, best_score

    def tick(self, **telemetry):
        rsfe = self.measure(**telemetry)
        self.tick_index += 1
        if len(self.recent_states) >= self.state_window and self.window_full_since_tick is None:
            self.window_full_since_tick = self.tick_index
        result = {"rsfe": rsfe, "operator": None, "category": None, "sign": None,
                   "warmed_up": len(self.recent_states) >= self.state_window}

        # BUG FOUND AND FIXED, TWICE (kept visible rather than silently
        # patched, per the honesty standard set in Papers II-IV):
        #
        # Round 1 bug: Shannon entropy over a growing deque isn't comparable
        # tick-to-tick until the deque is full -- h_max = log2(n) grows with
        # n during fill-up even when true diversity is constant. Produced a
        # false "Apple" match on a stable, cycling baseline.
        # Round 1 fix (insufficient on its own): gate matching on the
        # CURRENT tick's window being full.
        # Round 2 bug: that fix still compared a warmed-up tick against a
        # NOT-yet-warmed-up previous tick, so the first post-fix comparison
        # was still partly fill-up noise, not a real signal -- and it still
        # threw the same false Apple match one tick later.
        # Round 2 fix: require BOTH ticks in the comparison to postdate the
        # point the window first became full.
        both_sides_warmed_up = (
            self.window_full_since_tick is not None
            and self.tick_index > self.window_full_since_tick
        )
        if self.prev_rsfe is not None and both_sides_warmed_up:
            deltas = tuple(cur - prev for cur, prev in zip(rsfe, self.prev_rsfe))
            sign_vec = tuple(self._sign(d) for d in deltas)
            name, score = self._match(sign_vec)
            result["sign"] = sign_vec
            if name:
                result["operator"] = name
                result["category"] = CATEGORY[name]
                result["reading"] = OPERATORS[name]["reading"]
                result["match_strength"] = f"{score}/4 axes"
        self.prev_rsfe = rsfe
        self.log.append(result)
        return result

    def summary(self):
        hits = [r for r in self.log if r["operator"]]
        counts = Counter(r["operator"] for r in hits)
        lines = [f"Scanned {len(self.log)} ticks, {len(hits)} matched a known pattern."]
        for name, n in counts.most_common():
            lines.append(f"  {name:8s} x{n:<3d} -> {CATEGORY[name]}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Synthetic sample traces ("virus samples") -- each is a fabricated but
# internally consistent telemetry stream representing one failure pattern,
# used to check the scanner correctly IDs each signature.
# ---------------------------------------------------------------------------

def run_sample(name, ticks):
    print(f"\n=== Sample: {name} ===")
    # NOTE: state_window shortened to 4 (from 6) and each sample lengthened
    # below to 12 ticks. This is a direct, honest consequence of the Round 2
    # fix above: matching cannot start until AFTER the entropy window has
    # fully warmed up once, so a trace needs at least state_window+2 ticks
    # before any real signal can appear at all. Short traces with a large
    # window will legitimately produce zero matches -- that is not a bug,
    # it is the fix working, and it is a real constraint to know about
    # before pointing this at anything with few observations.
    scanner = OperatorScanner(scale_reference=10, state_window=4, epsilon=0.02)
    for t in ticks:
        result = scanner.tick(**t)
        r, s, f, e = result["rsfe"]
        tag = f"[{result['operator']}]" if result["operator"] else "[--]"
        print(f"  r={r:.2f} s={s:.2f} f={f:.2f} e={e:.2f}  {tag}"
              + (f"  {result['category']}" if result["operator"] else ""))
    print(scanner.summary())


def sample_sealed_component():
    # A component whose external admission rate steadily drops to zero
    # while nothing else about it changes -> should read as Onion / SEALED.
    ticks = []
    for i in range(12):
        attempted = 10
        admitted = max(0, 10 - i)
        ticks.append(dict(
            self_calls=2, total_calls=10, active_units=3,
            admitted_external=admitted, attempted_external=attempted,
            state_snapshot=f"state_{i}",
        ))
    return ticks


def sample_bottleneck():
    # Scale (active units) climbs while flow (admission rate) shrinks
    # -> should read as Hydra / BOTTLENECK.
    ticks = []
    for i in range(12):
        active = 2 + i
        attempted = 10
        admitted = max(1, 10 - i)
        ticks.append(dict(
            self_calls=1, total_calls=10, active_units=active,
            admitted_external=admitted, attempted_external=attempted,
            state_snapshot=f"state_{i}",
        ))
    return ticks


def sample_self_reference_collapse():
    # Self-calls climb toward total calls (r rising) while active units
    # shrink -> should read as Mirror / SELF-REFERENCE RISING.
    ticks = []
    for i in range(12):
        self_calls = min(10, 1 + i)
        active = max(1, 10 - i)
        ticks.append(dict(
            self_calls=self_calls, total_calls=10, active_units=active,
            admitted_external=8, attempted_external=10,
            state_snapshot=f"state_{i}",
        ))
    return ticks


def sample_healthy_baseline():
    # Everything fluctuates mildly with no sustained directional drift
    # -> should mostly NOT match any operator (system is stable).
    ticks = []
    for i in range(12):
        ticks.append(dict(
            self_calls=3, total_calls=10, active_units=4,
            admitted_external=9, attempted_external=10,
            state_snapshot=f"state_{i % 3}",  # cycling, not collapsing or exploding
        ))
    return ticks


if __name__ == "__main__":
    run_sample("Sealed component (expect Onion)", sample_sealed_component())
    run_sample("Bottleneck (expect Hydra)", sample_bottleneck())
    run_sample("Self-reference collapse (expect Mirror)", sample_self_reference_collapse())
    run_sample("Healthy baseline (expect mostly no match)", sample_healthy_baseline())
