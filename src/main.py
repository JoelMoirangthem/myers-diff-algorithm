import sys  # gives access to command-line args, stdout and stderr
from array import array  # compact integer arrays (used to save memory in the trace)


# ---------------------------------------------------------------------------
# 1. Reading files
# ---------------------------------------------------------------------------
class FileReader:
    """Reads a file as raw bytes and splits it into lines."""

    def read_lines(self, path):
        with open(path, "rb") as f:  # open in binary mode (no encoding/newline conversion)
            data = f.read()  # read the whole file as bytes
        lines = data.split(b"\n")  # split into lines on "\n" ("\r" is kept if present)
        if lines and lines[-1] == b"":  # file ended with "\n" -> split left an empty last piece
            lines.pop()  # remove that empty piece
        return lines  # list of lines (bytes), without the "\n"


# ---------------------------------------------------------------------------
# 2. The Myers diff algorithm
#    Works on any sequence: a list of lines, or a string (list of characters).
#    Returns a list of operations (kind, index_in_a, index_in_b):
#        (" ", i, j)    -> a[i] and b[j] are the same (kept)
#        ("-", i, None) -> a[i] was deleted
#        ("+", None, j) -> b[j] was inserted
# ---------------------------------------------------------------------------
class MyersDiffer:
    """Computes a minimal diff between two sequences."""

    def diff(self, a, b):
        n = len(a)  # length of the old sequence
        m = len(b)  # length of the new sequence

        prefix = self._common_prefix_length(a, b)  # how many items match at the start
        suffix = self._common_suffix_length(a, b, prefix)  # how many items match at the end

        a_start, a_end = prefix, n - suffix  # the part of a that is NOT in prefix/suffix
        b_start, b_end = prefix, m - suffix  # the part of b that is NOT in prefix/suffix

        ops = []  # final list of operations
        for i in range(prefix):  # every item in the common prefix...
            ops.append((" ", i, i))  # ...is kept (same index in a and b)
        ops.extend(self._diff_middle(a, b, a_start, a_end, b_start, b_end))  # diff the middle part
        for k in range(suffix):  # every item in the common suffix...
            ops.append((" ", a_end + k, b_end + k))  # ...is kept
        return ops  # done

    def _common_prefix_length(self, a, b):
        p = 0  # number of equal items found so far
        while p < len(a) and p < len(b) and a[p] == b[p]:  # walk forward while items are equal
            p += 1  # one more equal item
        return p  # length of the common prefix

    def _common_suffix_length(self, a, b, prefix):
        n = len(a)  # length of a
        m = len(b)  # length of b
        s = 0  # number of equal items found so far (from the end)
        # Stop before running into the prefix, so prefix and suffix never overlap.
        while s < n - prefix and s < m - prefix and a[n - 1 - s] == b[m - 1 - s]:
            s += 1  # one more equal item at the end
        return s  # length of the common suffix

    def _diff_middle(self, a, b, a_start, a_end, b_start, b_end):
        if a_start == a_end:  # nothing left in a -> everything left in b was inserted
            return [("+", None, j) for j in range(b_start, b_end)]  # all inserts
        if b_start == b_end:  # nothing left in b -> everything left in a was deleted
            return [("-", i, None) for i in range(a_start, a_end)]  # all deletes

        sub_a = a[a_start:a_end]  # middle part of a
        sub_b = b[b_start:b_end]  # middle part of b

        if self._nothing_in_common(sub_a, sub_b):  # shortcut: no item can ever match
            deletes = [("-", i, None) for i in range(a_start, a_end)]  # delete all of the middle of a
            inserts = [("+", None, j) for j in range(b_start, b_end)]  # insert all of the middle of b
            return deletes + inserts  # deletes first, then inserts

        core_ops = self._core(sub_a, sub_b)  # run real Myers on the middle part
        ops = []  # core results shifted back to full-sequence indexes
        for kind, ai, bi in core_ops:  # go through each operation
            if kind == " ":  # kept item
                ops.append((" ", ai + a_start, bi + b_start))  # shift both indexes
            elif kind == "-":  # deleted item
                ops.append(("-", ai + a_start, None))  # shift a index
            else:  # inserted item
                ops.append(("+", None, bi + b_start))  # shift b index
        return ops  # middle operations with correct indexes

    def _nothing_in_common(self, a, b):
        try:  # items must be hashable to put them in a set
            return set(a).isdisjoint(b)  # True if no item of a appears in b
        except TypeError:  # unhashable items -> can't use the shortcut
            return False  # fall back to the full algorithm

    # -----------------------------------------------------------------------
    # Core Myers algorithm (forward pass).
    #   Think of a grid: x = position in a, y = position in b.
    #   Moving right = delete a[x], moving down = insert b[y],
    #   moving diagonally = a[x] == b[y] (free, a "snake").
    #   Diagonal number k = x - y.
    #   Round d = we have used exactly d edits (deletes + inserts).
    #   furthest[k] = the largest x reached on diagonal k so far.
    # -----------------------------------------------------------------------
    def _core(self, a, b):
        n = len(a)  # length of a
        m = len(b)  # length of b
        if n == 0:  # a is empty -> all inserts
            return [("+", None, j) for j in range(m)]  # insert every item of b
        if m == 0:  # b is empty -> all deletes
            return [("-", i, None) for i in range(n)]  # delete every item of a

        max_d = n + m  # worst case: delete all of a and insert all of b
        offset = max_d + 1  # k can be negative, so we add offset to get a list index
        furthest = [0] * (2 * max_d + 3)  # furthest[offset + k] = best x on diagonal k
        trace = []  # trace[d] = saved copy of the diagonals after round d (for backtracking)

        for d in range(max_d + 1):  # try with 0 edits, then 1, then 2, ...
            for k in range(-d, d + 1, 2):  # in round d only diagonals -d, -d+2, ..., d are reachable
                ki = offset + k  # list index for diagonal k

                # Decide where we come from:
                #   down from diagonal k+1 (an insert), or right from diagonal k-1 (a delete).
                # At the left edge (k == -d) we can only come down.
                # At the right edge (k == d) we can only come right.
                # Otherwise pick whichever neighbour got further (ties go to "right"/delete).
                if k == -d or (k != d and furthest[ki - 1] < furthest[ki + 1]):
                    x = furthest[ki + 1]  # move down: x stays the same
                else:
                    x = furthest[ki - 1] + 1  # move right: x goes up by one
                y = x - k  # y follows from the diagonal number

                while x < n and y < m and a[x] == b[y]:  # follow the snake (equal items)
                    x += 1  # step forward in a
                    y += 1  # step forward in b

                furthest[ki] = x  # remember how far we got on this diagonal

                if x >= n and y >= m:  # reached the bottom-right corner -> done
                    trace.append(self._snapshot(furthest, offset, d))  # save this (last) round
                    return self._backtrack(trace, n, m)  # rebuild the edit path

            trace.append(self._snapshot(furthest, offset, d))  # save this round for backtracking

        raise AssertionError("unreachable")  # we always finish within n + m rounds

    def _snapshot(self, furthest, offset, d):
        # Save only diagonals -d, -d+2, ..., d (the ones used in round d).
        # So snapshot[(k + d) // 2] == furthest[k] after round d.
        return array("i", furthest[offset - d:offset + d + 1:2])  # compact int array

    # -----------------------------------------------------------------------
    # Backtracking: walk from the end (n, m) back to (0, 0) using the trace,
    # recording each edit and each snake. Operations are collected in reverse
    # and flipped at the end.
    # -----------------------------------------------------------------------
    def _backtrack(self, trace, n, m):
        reversed_ops = []  # operations collected from last to first
        x, y = n, m  # start at the bottom-right corner

        for d in range(len(trace) - 1, -1, -1):  # go back through the rounds
            row = trace[d]  # diagonals saved after round d
            k = x - y  # diagonal we are currently on
            idx = (k + d) // 2  # position of diagonal k inside row
            end_x = row[idx]  # x where round d ended on this diagonal (equals current x)

            if d == 0:  # round 0 had no edits, only an initial snake from (0, 0)
                for t in range(end_x - 1, -1, -1):  # walk that snake backwards
                    reversed_ops.append((" ", t, t))  # kept item (x == y on diagonal 0)
                break  # reached the start

            prev = trace[d - 1]  # diagonals saved after round d-1
            # In prev, diagonal k-1 is at idx-1 and diagonal k+1 is at idx.
            # Repeat the same decision the forward pass made.
            came_down = k == -d or (k != d and prev[idx - 1] < prev[idx])

            if came_down:  # we came down from diagonal k+1 -> an insert
                prev_x = prev[idx]  # x on diagonal k+1 before the move
                prev_y = prev_x - (k + 1)  # y on diagonal k+1 before the move
                snake_x = prev_x  # after moving down, x is unchanged
                snake_y = prev_y + 1  # after moving down, y is one more
                edit = ("+", None, prev_y)  # moving down inserts b[prev_y]
            else:  # we came right from diagonal k-1 -> a delete
                prev_x = prev[idx - 1]  # x on diagonal k-1 before the move
                prev_y = prev_x - (k - 1)  # y on diagonal k-1 before the move
                snake_x = prev_x + 1  # after moving right, x is one more
                snake_y = prev_y  # after moving right, y is unchanged
                edit = ("-", prev_x, None)  # moving right deletes a[prev_x]

            for t in range(end_x - snake_x - 1, -1, -1):  # walk the snake after the edit backwards
                reversed_ops.append((" ", snake_x + t, snake_y + t))  # kept item
            reversed_ops.append(edit)  # then the edit itself

            x, y = prev_x, prev_y  # jump to where this round started

        reversed_ops.reverse()  # flip into first-to-last order
        return reversed_ops  # final operation list


# ---------------------------------------------------------------------------
# 3. Grouping operations into blocks
#    A "change block" is a run of deletes/inserts between two kept lines.
# ---------------------------------------------------------------------------
def walk_blocks(ops, a_lines, b_lines):
    """Yields ("same", line) or ("change", deleted_lines, inserted_lines)."""
    deleted = []  # deleted lines in the current block
    inserted = []  # inserted lines in the current block
    for kind, ai, bi in ops:  # go through every operation in order
        if kind == " ":  # a kept line ends the current block
            if deleted or inserted:  # only report a block that has something in it
                yield ("change", deleted, inserted)  # hand the block to the caller
                deleted, inserted = [], []  # start a new empty block
            yield ("same", a_lines[ai])  # then the kept line
        elif kind == "-":  # deleted line
            deleted.append(a_lines[ai])  # add to the current block
        else:  # inserted line
            inserted.append(b_lines[bi])  # add to the current block
    if deleted or inserted:  # a block may still be open at the end
        yield ("change", deleted, inserted)  # report it


# ---------------------------------------------------------------------------
# 4. Output for "lines" mode
# ---------------------------------------------------------------------------
class LineOutput:
    """Builds the line diff: ' ' kept, '-' deleted, '+' inserted."""

    def build(self, ops, a_lines, b_lines):
        out = []  # pieces of output (bytes)
        for block in walk_blocks(ops, a_lines, b_lines):  # go block by block
            if block[0] == "same":  # kept line
                out.append(b" " + block[1] + b"\n")  # print with a space prefix
            else:  # change block
                _, deleted, inserted = block  # unpack the block
                for line in deleted:  # all deletes first
                    out.append(b"-" + line + b"\n")  # print with "-" prefix
                for line in inserted:  # then all inserts
                    out.append(b"+" + line + b"\n")  # print with "+" prefix
        return b"".join(out)  # join into one bytes object (b"" if nothing)


# ---------------------------------------------------------------------------
# 5. Character ranges for one (deleted line, inserted line) pair
# ---------------------------------------------------------------------------
class RangeOutput:
    """Finds which characters changed inside a paired line."""

    def __init__(self, differ):
        self._differ = differ  # the same Myers differ, reused on characters

    def for_pair(self, old_bytes, new_bytes):
        old_text = old_bytes.decode("utf-8")  # bytes -> text (so we compare characters, not bytes)
        new_text = new_bytes.decode("utf-8")  # same for the new line
        ops = self._differ.diff(old_text, new_text)  # diff the two strings character by character
        deleted_positions = []  # character positions removed from the old line
        inserted_positions = []  # character positions added in the new line
        for kind, ai, bi in ops:  # go through each character operation
            if kind == "-":  # character deleted
                deleted_positions.append(ai)  # remember its position in the old line
            elif kind == "+":  # character inserted
                inserted_positions.append(bi)  # remember its position in the new line
        return (self._format(deleted_positions), self._format(inserted_positions))  # as text ranges

    @staticmethod
    def _format(positions):
        # Turns sorted positions into ranges "start-end" (end is exclusive).
        # Example: [0, 1, 2, 5] -> "0-3,5-6". No positions -> ".".
        if not positions:  # nothing changed on this side
            return "."  # placeholder
        ranges = []  # finished ranges as text
        start = positions[0]  # start of the current range
        last = positions[0]  # last position in the current range
        for pos in positions[1:]:  # look at the remaining positions
            if pos == last + 1:  # continues the current range
                last = pos  # extend it
                continue  # next position
            ranges.append(f"{start}-{last + 1}")  # gap found -> close the current range
            start = pos  # begin a new range
            last = pos  # it has one position so far
        ranges.append(f"{start}-{last + 1}")  # close the final range
        return ",".join(ranges)  # join ranges with commas


# ---------------------------------------------------------------------------
# 6. Output for "highlight" mode
# ---------------------------------------------------------------------------
class HighlightOutput:
    """Like LineOutput, but adds a '?' line with character ranges for paired lines."""

    def __init__(self, range_output):
        self._ranges = range_output  # computes character ranges for a pair

    def build(self, ops, a_lines, b_lines):
        out = []  # pieces of output (bytes)
        for block in walk_blocks(ops, a_lines, b_lines):  # go block by block
            if block[0] == "same":  # kept line
                out.append(b" " + block[1] + b"\n")  # print with a space prefix
                continue  # next block
            _, deleted, inserted = block  # unpack the change block
            for line in deleted:  # all deletes first
                out.append(b"-" + line + b"\n")  # print with "-" prefix
            pairs = min(len(deleted), len(inserted))  # pair 1st delete with 1st insert, 2nd with 2nd, ...
            for i, line in enumerate(inserted):  # then each insert
                out.append(b"+" + line + b"\n")  # print with "+" prefix
                if i < pairs:  # this insert has a matching delete
                    old_r, new_r = self._ranges.for_pair(deleted[i], line)  # changed character ranges
                    out.append(b"? " + old_r.encode() + b" | " + new_r.encode() + b"\n")  # "? old | new"
        return b"".join(out)  # join into one bytes object (b"" if nothing)


# ---------------------------------------------------------------------------
# 7. The application: read -> diff -> print
# ---------------------------------------------------------------------------
class DiffApp:
    """Connects reading, diffing and printing."""

    def __init__(self, reader, differ):
        self._reader = reader  # reads files into lines
        self._differ = differ  # computes the diff
        self._lines_out = LineOutput()  # formatter for "lines" mode
        self._highlight_out = HighlightOutput(RangeOutput(differ))  # formatter for "highlight" mode

    def run_lines(self, a_path, b_path, out_buf):
        return self._run(a_path, b_path, out_buf, self._lines_out)  # use the lines formatter

    def run_highlight(self, a_path, b_path, out_buf):
        return self._run(a_path, b_path, out_buf, self._highlight_out)  # use the highlight formatter

    def _run(self, a_path, b_path, out_buf, formatter):
        try:  # reading may fail (missing file, no permission, ...)
            a = self._reader.read_lines(a_path)  # lines of the old file
            b = self._reader.read_lines(b_path)  # lines of the new file
        except OSError as e:  # file could not be read
            print(f"error: cannot read file: {e}", file=sys.stderr)  # report the error
            return 2  # exit code 2 = error
        ops = self._differ.diff(a, b)  # compute the line diff
        data = formatter.build(ops, a, b)  # turn it into output bytes
        if data:  # only write if there is something
            out_buf.write(data)  # write raw bytes to stdout
        return 0  # exit code 0 = success (even if files differ)


# ---------------------------------------------------------------------------
# 8. Command-line entry point
# ---------------------------------------------------------------------------
def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):  # check arguments
        print("usage: main.py lines|highlight A_PATH B_PATH", file=sys.stderr)  # show usage
        return 2  # exit code 2 = bad usage
    command, a_path, b_path = sys.argv[1:]  # mode, old file, new file
    app = DiffApp(FileReader(), MyersDiffer())  # build the app with its parts
    if command == "lines":  # "lines" mode
        return app.run_lines(a_path, b_path, sys.stdout.buffer)  # plain line diff
    return app.run_highlight(a_path, b_path, sys.stdout.buffer)  # line diff + character ranges


raise SystemExit(main())  # run main() and exit with its return code (same as the original)
