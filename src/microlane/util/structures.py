from math import atan2, cos, sin, sqrt

# Data structures and algorithms decoupled from synthesis/implementation logic


class PushbackIter:
    """enhanced iterator that allows pushing items back (used for look-ahead)"""

    def __init__(self, source):
        self.it = iter(source)
        self.queue = []

    def __iter__(self):
        return self

    def __next__(self):
        next_value = self.queue.pop() if self.queue else next(self.it)
        return next_value

    def pushback(self, item):
        self.queue.append(item)


class UnionFind:
    """union-find data structure with path splitting & union by size"""

    def __init__(self):
        self.parent = {}
        self.size = {}

    def add(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.size[x] = 1

    def find(self, x):
        while self.parent[x] != x:
            p = self.parent[x]
            self.parent[x] = self.parent[p]
            x = p
        return x

    def union(self, x, y, ignore_size=False):
        x = self.find(x)
        y = self.find(y)
        if x == y:
            return x
        if not ignore_size:
            if self.size[x] < self.size[y]:
                x, y = y, x
        self.parent[y] = x
        self.size[x] += self.size[y]
        return x

    def sets(self):
        keys = sorted(self.parent.keys())
        sets = {}
        for x in keys:
            root = self.find(x)
            if root not in sets:
                sets[root] = [root]
            if x != root:
                sets[root].append(x)
        return sorted(sets.values())

    def __repr__(self):
        return f"<UnionFind {self.sets()}>"


class DataClass:
    """Micropython compatible substitute for Python's dataclass"""

    _attributes = None
    _defaults = {}
    _show_always = set()

    def __init__(self, **kwargs):
        if self._attributes is None:
            raise RuntimeError(
                "Trying to instantiate a DataClass subclass with _attributes undefined"
            )
        for attr in kwargs:
            if attr not in self._attributes:
                raise RuntimeError(
                    f"Unexpected attribute {attr} for {self.__class__.__name__}"
                )
        for attr in self._attributes:
            if attr in kwargs:
                setattr(self, attr, kwargs[attr])
            elif attr in self._defaults:
                setattr(self, attr, self._defaults[attr])
            else:
                raise RuntimeError(
                    f"Missing attribute {attr} for {self.__class__.__name__}"
                )

    def __repr__(self):
        d = ", ".join(
            f"{attr}={value!r}"
            for attr, value in (
                (attr, getattr(self, attr)) for attr in self._attributes
            )
            if attr not in self._defaults
            or attr in self._show_always
            or self._defaults[attr] != value
        )
        return f"{self.__class__.__name__}({d})"

    @staticmethod
    def _copy(obj):
        if obj is None or type(obj) in (bool, int, range, str):
            return obj
        elif type(obj) in (list, tuple, dict, set):
            return type(obj)(obj)
        elif hasattr(obj, "copy"):
            return obj.copy()
        else:
            raise NotImplementedError(
                f"Don't know how to copy object of type {type(obj)}: {obj}"
            )

    def copy(self):
        return self.__class__(
            **{attr: self._copy(getattr(self, attr)) for attr in self._attributes}
        )


class Point(DataClass):
    """2d point"""

    _attributes = ["x", "y"]

    def as_tuple(self):
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, value):
        x, y = value
        return cls(x=x, y=y)

    def shifted(self, dx, dy):
        return Point(x=self.x + dx, y=self.y + dy)


class Rect(DataClass):
    """axis-aligned rectangle"""

    _attributes = ["x1", "y1", "x2", "y2", "data"]
    _defaults = {"data": None}

    def as_tuple(self):
        return (self.x1, self.y1, self.x2, self.y2)

    @classmethod
    def from_tuple(cls, value):
        x1, y1, x2, y2 = value
        return cls(x1=x1, y1=y1, x2=x2, y2=y2)

    def with_data(self, data):
        return Rect(x1=self.x1, y1=self.y1, x2=self.x2, y2=self.y2, data=data)

    def contains_rect(self, other):
        return (
            self.x1 <= other.x1
            and other.x2 <= self.x2
            and self.y1 <= other.y1
            and other.y2 <= self.y2
        )

    def touches_rect(self, other):
        return (
            self.x1 <= other.x2
            and other.x1 <= self.x2
            and self.y1 <= other.y2
            and other.y1 <= self.y2
        )

    def intersects_rect(self, other):
        return (
            self.x1 < other.x2
            and other.x1 < self.x2
            and self.y1 < other.y2
            and other.y1 < self.y2
        )

    def shifted(self, dx, dy):
        return Rect(
            x1=self.x1 + dx,
            y1=self.y1 + dy,
            x2=self.x2 + dx,
            y2=self.y2 + dy,
            data=self.data,
        )

    def bloated(self, d):
        return Rect(
            x1=self.x1 - d,
            y1=self.y1 - d,
            x2=self.x2 + d,
            y2=self.y2 + d,
            data=self.data,
        )

    def intersection(self, other):
        res = Rect(
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
            x2=min(self.x2, other.x2),
            y2=min(self.y2, other.y2),
        )
        assert res.x1 < res.x2
        assert res.y1 < res.y2
        return res

    def size(self):
        return (self.x2 - self.x1, self.y2 - self.y1)

    def center(self):
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def center_offset(self, both=False):
        cx, cy = self.center()
        rx1, ry1, rx2, ry2 = self.x1 - cx, self.y1 - cy, self.x2 - cx, self.y2 - cy
        rect = Rect(x1=rx1, y1=ry1, x2=rx2, y2=ry2)
        if both:
            return (cx, cy), rect
        else:
            return rect

    def slide_calc(self, other, epsilon, tie_breaker):
        # calculate direction & amount the rectangle needs to slide
        # to touch the other one from the outside (in Euclidean space)
        scx, scy = self.center()
        ocx, ocy = other.center()
        dx = ocx - scx
        dy = ocy - scy
        dsq = dx**2 + dy**2
        d = sqrt(dsq)  # no hypot in micropython
        if dsq >= epsilon**2:
            phi = atan2(dy, dx)
            ux, uy = cos(phi), sin(phi)
        elif tie_breaker >= 0:
            ux, uy = cos(tie_breaker), sin(tie_breaker)
        else:
            ux, uy = -cos(tie_breaker), sin(tie_breaker)
        tw = (self.x2 - self.x1) + (other.x2 - other.x1)
        th = (self.y2 - self.y1) + (other.y2 - other.y1)
        if tw * abs(uy) < th * abs(ux):
            td = tw / 2 / abs(ux)
        else:
            td = th / 2 / abs(uy)
        return d, td, (ux, uy)


class QuadTree:
    """data structure to store a set of rectangles with efficient queries for containment and intersection"""

    def __init__(self, *rects):
        self.entries = {}
        self.parents = {}
        self.children = {}
        self.top_level = 0
        self.top_level_entries = set()
        for rect in rects:
            self.add_rect(rect)

    def _dump(self, tag, *extras):
        if getattr(self, "_dumping", False):
            return
        self._dumping = True
        print(f"[{tag}] {self.entries=}")
        print(f"[{tag}] {self.parents=}")
        print(f"[{tag}] {self.children=}")
        print(f"[{tag}] {self.top_level=}")
        print(f"[{tag}] {self.top_level_entries=}")
        print(f"[{tag}] {self=}")
        print(f"[{tag}] {extras=}")
        self._dumping = False

    @staticmethod
    def _get_parent(entry):
        level, x, y = entry
        shift = level % 2
        return (level + 1, (x + shift) // 2, (y + shift) // 2)

    def _add_parent(self, entry):
        parent = self._get_parent(entry)
        assert entry not in self.parents
        self.parents[entry] = parent
        clist = self.children.setdefault(parent, [])
        assert entry not in clist
        clist.append(entry)
        return parent

    def _add_level(self):
        new_top_level_entries = set()
        for entry in sorted(self.top_level_entries):
            assert entry[0] == self.top_level
            parent = self._add_parent(entry)
            new_top_level_entries.add(parent)
        self.top_level_entries = new_top_level_entries
        self.top_level += 1

    def _add_parents(self, entry):
        while entry[0] > self.top_level:
            self._add_level()
        while entry[0] < self.top_level:
            if entry in self.parents:
                return
            entry = self._add_parent(entry)
        self.top_level_entries.add(entry)

    def _add_entry(self, entry, data):
        dlist = self.entries.setdefault(entry, [])
        dlist.append(data)
        self._add_parents(entry)

    def _iter_children(self, entry):
        while entry[0] > self.top_level:
            self._add_level()
        yield from self.entries.get(entry, [])
        for child in self.children.get(entry, []):
            yield from self._iter_children(child)

    def _iter_children_and_parents(self, entry):
        yield from self._iter_children(entry)
        parent = self._get_parent(entry)
        while parent[0] <= self.top_level:
            yield from self.entries.get(parent, [])
            parent = self._get_parent(parent)

    @staticmethod
    def _find_rect_entry(rect):
        entry1, entry2 = (0, rect.x1, rect.y1), (0, rect.x2, rect.y2)
        while entry1 != entry2:
            entry1 = __class__._get_parent(entry1)
            entry2 = __class__._get_parent(entry2)
        return entry1

    def add_rect(self, rect):
        self._add_entry(self._find_rect_entry(rect), rect)

    def query_contained_rects(self, rect):
        for other in self._iter_children(self._find_rect_entry(rect)):
            if rect.contains_rect(other):
                yield other

    def query_intersecting_rects(self, rect):
        for other in self._iter_children_and_parents(self._find_rect_entry(rect)):
            if rect.intersects_rect(other):
                yield other

    def query_all_rects(self):
        for entry in self.top_level_entries:
            yield from self._iter_children(entry)

    def __repr__(self):
        return (
            "QuadTree(" + ", ".join(repr(rect) for rect in self.query_all_rects()) + ")"
        )


class ReferenceQuadTree:
    """slow reference implementation of QuadTree, compared against the regular version in debug mode"""

    def __init__(self, *rects):
        self.rects = list(rects)

    def add_rect(self, rect):
        self.rects.append(rect)

    def query_contained_rects(self, rect):
        return [other for other in self.rects if rect.intersects_rect(other)]

    def query_intersecting_rects(self, rect):
        return [other for other in self.rects if rect.intersects_rect(other)]

    def query_all_rects(self):
        return self.rects

    def __repr__(self):
        return "ReferenceQuadTree(" + ", ".join(repr(rect) for rect in self.rects) + ")"


class DebugQuadTree:
    """keeps a parallel instance of QuadTree and ReferenceQuadTree, checking if they return the same results"""

    def __init__(self, *rects):
        self.qt = QuadTree(*rects)
        self.ref = ReferenceQuadTree(*rects)

    def add_rect(self, rect):
        self.qt.add_rect(rect)
        self.ref.add_rect(rect)

    def query_contained_rects(self, rect):
        result = list(self.qt.query_contained_rects(rect))
        reference = list(self.ref.query_contained_rects(rect))
        assert sorted(result, key=Rect.as_tuple) == sorted(reference, key=Rect.as_tuple)
        return result

    def query_intersecting_rects(self, rect):
        result = list(self.qt.query_intersecting_rects(rect))
        reference = list(self.ref.query_intersecting_rects(rect))
        assert sorted(result, key=Rect.as_tuple) == sorted(reference, key=Rect.as_tuple)
        return result

    def query_all_rects(self):
        result = list(self.qt.query_all_rects())
        reference = list(self.ref.query_all_rects())
        assert sorted(result, key=Rect.as_tuple) == sorted(reference, key=Rect.as_tuple)
        return result

    def __repr__(self):
        return "DebugQuadTree(" + ", ".join(repr(rect) for rect in self.ref.rects) + ")"
