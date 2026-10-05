import sys
from array import array


class FileReader:
    """Read a file as raw bytes and split into lines (SRP: file IO only)."""

    def read_lines(self, path):
        with open(path, "rb") as f:
            data = f.read()
        parts = data.split(b"\n")
        if parts and parts[-1] == b"":
            parts.pop()
        return parts


class MyersDiffer:
    """Minimal O(ND) diff for any sequence (SRP: diff only, OCP: generic)."""

    def diff(self, a, b):
        n = len(a)
        m = len(b)
        p = 0
        while p < n and p < m and a[p] == b[p]:
            p += 1
        s = 0
        while s < n - p and s < m - p and a[n - 1 - s] == b[m - 1 - s]:
            s += 1
        ops = []
        for i in range(p):
            ops.append((" ", i, i))
        mid_a_start = p
        mid_a_end = n - s
        mid_b_start = p
        mid_b_end = m - s
        if mid_a_start == mid_a_end:
            for j in range(mid_b_start, mid_b_end):
                ops.append(("+", None, j))
        elif mid_b_start == mid_b_end:
            for i in range(mid_a_start, mid_a_end):
                ops.append(("-", i, None))
        else:
            sub_a = a[mid_a_start:mid_a_end]
            sub_b = b[mid_b_start:mid_b_end]
            try:
                if set(sub_a).isdisjoint(sub_b):
                    for i in range(mid_a_start, mid_a_end):
                        ops.append(("-", i, None))
                    for j in range(mid_b_start, mid_b_end):
                        ops.append(("+", None, j))
                    for k in range(s):
                        ops.append((" ", n - s + k, m - s + k))
                    return ops
            except TypeError:
                pass
            mid_ops = self._core(sub_a, sub_b)
            for kind, ai, bi in mid_ops:
                if kind == " ":
                    ops.append((" ", ai + mid_a_start, bi + mid_b_start))
                elif kind == "-":
                    ops.append(("-", ai + mid_a_start, None))
                else:
                    ops.append(("+", None, bi + mid_b_start))
        for k in range(s):
            ops.append((" ", n - s + k, m - s + k))
        return ops

    def _core(self, a, b):
        n = len(a)
        m = len(b)
        if n == 0:
            return [("+", None, j) for j in range(m)]
        if m == 0:
            return [("-", i, None) for i in range(n)]
        # V is one flat list indexed by k + off (no dict overhead).
        # trace[d] is a compact int array holding only the d+1 diagonals
        # k = -d, -d+2, ..., d, so trace[d][(k + d) // 2] == V[k] after round d.
        # Memory is about 2*D*D bytes instead of a dict copy per round.
        max_d = n + m
        off = max_d + 1
        v = [0] * (2 * max_d + 3)
        v[off + 1] = 0
        trace = []
        for d in range(max_d + 1):
            for k in range(-d, d + 1, 2):
                ki = off + k
                if k == -d or (k != d and v[ki - 1] < v[ki + 1]):
                    x = v[ki + 1]
                else:
                    x = v[ki - 1] + 1
                y = x - k
                while x < n and y < m and a[x] == b[y]:
                    x += 1
                    y += 1
                v[ki] = x
                if x >= n and y >= m:
                    trace.append(array("i", v[off - d:off + d + 1:2]))
                    return self._backtrack(trace, n, m)
            trace.append(array("i", v[off - d:off + d + 1:2]))
        raise AssertionError("unreachable")

    def _backtrack(self, trace, n, m):
        rev = []
        x = n
        y = m
        for d in range(len(trace) - 1, -1, -1):
            cur = trace[d]
            k = x - y
            idx = (k + d) // 2
            x1 = cur[idx]
            y1 = x1 - k
            if d == 0:
                for t in range(x1 - 1, -1, -1):
                    rev.append((" ", t, t))
                x = 0
                y = 0
                break
            prev = trace[d - 1]
            # In prev (round d-1), diagonal k-1 is at idx-1 and k+1 is at idx.
            if k == -d or (k != d and prev[idx - 1] < prev[idx]):
                pk = k + 1
                xp = prev[idx]
                yp = xp - pk
                x0 = xp
                y0 = x0 - k
                for t in range(x1 - x0 - 1, -1, -1):
                    rev.append((" ", x0 + t, y0 + t))
                rev.append(("+", None, yp))
                x = xp
                y = yp
            else:
                pk = k - 1
                xp = prev[idx - 1]
                yp = xp - pk
                x0 = xp + 1
                y0 = yp
                for t in range(x1 - x0 - 1, -1, -1):
                    rev.append((" ", x0 + t, y0 + t))
                rev.append(("-", xp, None))
                x = xp
                y = yp
        rev.reverse()
        return rev


class LineOutput:
    """Build Part A bytes with delete-first blocks (SRP: formatting only)."""

    def build(self, ops, a_lines, b_lines):
        chunks = []
        dels = []
        inss = []
        SP = b" "
        DL = b"-"
        IN = b"+"
        NL = b"\n"

        def flush():
            for ln in dels:
                chunks.append(DL + ln + NL)
            for ln in inss:
                chunks.append(IN + ln + NL)
            dels.clear()
            inss.clear()

        for kind, ai, bi in ops:
            if kind == " ":
                flush()
                chunks.append(SP + a_lines[ai] + NL)
            elif kind == "-":
                dels.append(a_lines[ai])
            else:
                inss.append(b_lines[bi])
        flush()
        if chunks:
            return b"".join(chunks)
        return b""


class RangeOutput:
    """Char ranges for one paired line (SRP: range formatting only)."""

    def __init__(self, differ):
        self._differ = differ

    def for_pair(self, old_bytes, new_bytes):
        old_s = old_bytes.decode("utf-8")
        new_s = new_bytes.decode("utf-8")
        ops = self._differ.diff(old_s, new_s)
        del_idx = []
        ins_idx = []
        for kind, ai, bi in ops:
            if kind == "-":
                del_idx.append(ai)
            elif kind == "+":
                ins_idx.append(bi)
        return (self._fmt(del_idx), self._fmt(ins_idx))

    @staticmethod
    def _fmt(idx):
        if not idx:
            return "."
        parts = []
        s = idx[0]
        p = idx[0]
        for v in idx[1:]:
            if v == p + 1:
                p = v
                continue
            parts.append(f"{s}-{p + 1}")
            s = v
            p = v
        parts.append(f"{s}-{p + 1}")
        return ",".join(parts)


class DiffApp:
    """Orchestrate read -> diff -> output (SRP: workflow, DIP: injected parts)."""

    def __init__(self, reader, differ):
        self._reader = reader
        self._differ = differ
        self._lines_out = LineOutput()
        self._range_out = RangeOutput(differ)

    def run_lines(self, a_path, b_path, out_buf):
        try:
            a = self._reader.read_lines(a_path)
            b = self._reader.read_lines(b_path)
        except OSError as e:
            print(f"error: cannot read file: {e}", file=sys.stderr)
            return 2
        ops = self._differ.diff(a, b)
        data = self._lines_out.build(ops, a, b)
        if data:
            out_buf.write(data)
        return 0

    def run_highlight(self, a_path, b_path, out_buf):
        try:
            a = self._reader.read_lines(a_path)
            b = self._reader.read_lines(b_path)
        except OSError as e:
            print(f"error: cannot read file: {e}", file=sys.stderr)
            return 2
        ops = self._differ.diff(a, b)
        chunks = []
        dels = []
        inss = []
        SP = b" "
        DL = b"-"
        IN = b"+"
        Q = b"?"
        NL = b"\n"

        def flush_block():
            n_del = len(dels)
            n_ins = len(inss)
            for ln in dels:
                chunks.append(DL + ln + NL)
            pairs = n_del if n_del < n_ins else n_ins
            for i, ln in enumerate(inss):
                chunks.append(IN + ln + NL)
                if i < pairs:
                    ro, rn = self._range_out.for_pair(dels[i], ln)
                    chunks.append(Q + b" " + ro.encode() + b" | " + rn.encode() + NL)
            dels.clear()
            inss.clear()

        for kind, ai, bi in ops:
            if kind == " ":
                flush_block()
                chunks.append(SP + a[ai] + NL)
            elif kind == "-":
                dels.append(a[ai])
            else:
                inss.append(b[bi])
        flush_block()
        if chunks:
            out_buf.write(b"".join(chunks))
        return 0


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        print("usage: main.py lines|highlight A_PATH B_PATH", file=sys.stderr)
        return 2
    command, a_path, b_path = sys.argv[1:]
    app = DiffApp(FileReader(), MyersDiffer())
    if command == "lines":
        return app.run_lines(a_path, b_path, sys.stdout.buffer)
    return app.run_highlight(a_path, b_path, sys.stdout.buffer)


raise SystemExit(main())
