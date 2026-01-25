import struct

GDS_RECORD_TYPES = {
    0x0002: "HEADER",
    0x0102: "BGNLIB",
    0x0206: "LIBNAME",
    0x0305: "UNITS",
    0x0400: "ENDLIB",
    0x0502: "BGNSTR",
    0x0606: "STRNAME",
    0x0700: "ENDSTR",
    0x0800: "BOUNDARY",
    0x0900: "PATH",
    0x0A00: "SREF",
    0x0B00: "AREF",
    0x0C00: "TEXT",
    0x0D02: "LAYER",
    0x0E02: "DATATYPE",
    0x0F03: "WIDTH",
    0x1003: "XY",
    0x1100: "ENDEL",
    0x1206: "SNAME",
    0x1302: "COLROW",
    0x1602: "TEXTTYPE",
    0x1701: "PRESENTATION",
    0x1906: "STRING",
    0x1A01: "STRANS",
    0x1B05: "MAG",
    0x1C05: "ANGLE",
    0x2102: "PATHTYPE",
    0x2B02: "PROPATTR",
    0x2C06: "PROPVALUE",
    0x3003: "BGNEXTN",
    0x3103: "ENDEXTN",
}


class GDS:
    """enum for gds record types"""

    lookup = GDS_RECORD_TYPES


for k, v in GDS_RECORD_TYPES.items():
    setattr(GDS, v, k)


def encode_real(number):
    """encode a floating-point number using the 8-byte real format used by gds"""
    (raw,) = struct.unpack(">Q", struct.pack(">d", number))
    bits = f"{raw:064b}"
    if raw:
        sign, exponent, mantissa = bits[:1], bits[1:12], bits[12:]
        exponent = int(exponent, 2) - 1023
        shift, exponent = 3 - exponent % 4, exponent // 4
        assert -65 <= exponent <= 62
        exp_shifted = exponent + 65
        bits = (
            sign
            + f"{exp_shifted:07b}"
            + "0" * shift
            + "1"
            + mantissa
            + "0" * (3 - shift)
        )
    return struct.pack(">Q", int(bits, 2))


def decode_real(data):
    """decode a floating-point number from the 8-byte real format used by gds"""
    (raw,) = struct.unpack(">Q", data)
    bits = f"{raw:064b}"
    if raw:
        sign, exponent, mantissa = bits[:1], bits[1:8], bits[8:]
        exponent = int(exponent, 2) - 65
        shift = mantissa.find("1")
        assert 0 <= shift <= 3
        exponent = exponent * 4 + (3 - shift)
        exp_shifted = exponent + 1023
        bits = sign + f"{exp_shifted:011b}" + mantissa[1 + shift : 53 + shift]
    return struct.unpack(">d", struct.pack(">Q", int(bits, 2)))[0]


def array_generator(base_rect, shift_vectors):
    """helper for generating a multi-dimensional array of shifted rectangles"""
    (p1x, p1y), (p2x, p2y) = base_rect
    if not shift_vectors:
        yield base_rect
        return
    dims = len(shift_vectors)
    repeat, dx, dy = zip(*((r, d, x) for r, (d, x) in shift_vectors))
    indices = [0] * dims
    while True:
        sx = sum(i * d for i, d in zip(indices, dx))
        sy = sum(i * d for i, d in zip(indices, dy))
        yield (p1x + sx, p1y + sy), (p2x + sx, p2y + sy)
        pos = dims - 1
        while pos >= 0 and indices[pos] == repeat[pos] - 1:
            indices[pos] = 0
            pos -= 1
        if pos < 0:
            break
        indices[pos] += 1


class GdsLibrary:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.file = open(self.path, "rb")
        self.cell_offsets = {}
        record_type = None
        cell_name = None
        while record_type != GDS.ENDLIB:
            header = self.file.read(4)
            record_length, record_type = struct.unpack(">HH", header)
            if record_type == GDS.BGNSTR:
                cell_offset = self.file.tell() - 4
            if record_type == GDS.ENDSTR:
                cell_bytes = self.file.tell() - cell_offset
                assert cell_name is not None
                self.cell_offsets[cell_name] = (cell_offset, cell_bytes)
                cell_name = None
            if record_type == GDS.STRNAME:
                cell_name = self.file.read(record_length - 4).rstrip(b"\0").decode()
            else:
                self.file.seek(record_length - 4, 1)  # relative seek
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.close()

    def get_cell(self, name, chunk=512):
        if name not in self.cell_offsets:
            raise KeyError(f"Cell {name} not found in library {self.path}")
        cell_offset, cell_bytes = self.cell_offsets[name]
        self.file.seek(cell_offset)
        while cell_bytes >= chunk:
            yield self.file.read(chunk)
            cell_bytes -= chunk
        if cell_bytes:
            yield self.file.read(cell_bytes)


class GdsWriter:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.file = open(self.path, "wb")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.close()

    def write_record(self, record_type, data):
        record_length = len(data) + 4
        padding = b""
        if record_length % 2 == 1:
            record_length += 1
            padding = b"\0"
        header = struct.pack(">HH", record_length, record_type)
        self.file.write(header)
        self.file.write(data)
        if padding:
            self.file.write(padding)

    def write_header(self, lib_name):
        gds_version = 3
        modification_time = (70, 1, 1, 0, 0, 0)
        access_time = (70, 1, 1, 0, 0, 0)
        db_unit_in_user_units = 0.001
        db_unit_in_meters = 1e-9
        self.write_record(GDS.HEADER, struct.pack(">H", gds_version))
        self.write_record(
            GDS.BGNLIB, struct.pack(">HHHHHHHHHHHH", *modification_time, *access_time)
        )
        self.write_record(GDS.LIBNAME, lib_name.encode())
        self.write_record(
            GDS.UNITS,
            encode_real(db_unit_in_user_units) + encode_real(db_unit_in_meters),
        )

    def write_footer(self):
        self.write_record(GDS.ENDLIB, b"")

    def stream_from_library(self, generator):
        for chunk in generator:
            self.file.write(chunk)

    def start_cell(self, cell_name):
        modification_time = (70, 1, 1, 0, 0, 0)
        access_time = (70, 1, 1, 0, 0, 0)
        self.write_record(
            GDS.BGNSTR, struct.pack(">HHHHHHHHHHHH", *modification_time, *access_time)
        )
        self.write_record(GDS.STRNAME, cell_name.encode())

    def end_cell(self):
        self.write_record(GDS.ENDSTR, b"")

    def add_instance(self, cell_name, instance_name, x, y, flip=False, flop=False):
        mirror = flip != flop
        self.write_record(GDS.SREF, b"")
        self.write_record(GDS.SNAME, cell_name.encode())
        self.write_record(GDS.STRANS, b"\x80\0" if mirror else b"\0\0")
        if flip:
            self.write_record(GDS.ANGLE, encode_real(180))
        self.write_record(GDS.XY, struct.pack(">ii", x, y))
        if instance_name is not None:
            self.write_record(GDS.PROPATTR, b"\0\x3d")
            self.write_record(GDS.PROPVALUE, instance_name.encode())
        self.write_record(GDS.ENDEL, b"")

    def add_polygon(self, layer, data_type, points):
        self.write_record(GDS.BOUNDARY, b"")
        self.write_record(GDS.LAYER, struct.pack(">H", layer))
        self.write_record(GDS.DATATYPE, struct.pack(">H", data_type))
        self.write_record(GDS.XY, b"".join(struct.pack(">ii", x, y) for x, y in points))
        self.write_record(GDS.ENDEL, b"")

    def add_rect(self, layer, data_type, p1, p2):
        (x1, y1), (x2, y2) = p1, p2
        self.add_polygon(
            layer, data_type, ((x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1))
        )

    def add_text(self, layer, text_type, point, text, size, angle):
        x, y = point
        self.write_record(GDS.TEXT, b"")
        self.write_record(GDS.LAYER, struct.pack(">H", layer))
        self.write_record(GDS.TEXTTYPE, struct.pack(">H", text_type))
        self.write_record(GDS.PRESENTATION, b"\0\x05")
        self.write_record(GDS.STRANS, b"\0\0")
        self.write_record(GDS.MAG, encode_real(size))
        self.write_record(GDS.ANGLE, encode_real(angle))
        self.write_record(GDS.XY, struct.pack(">ii", x, y))
        self.write_record(GDS.STRING, text.encode())
        self.write_record(GDS.ENDEL, b"")

    def add_manual_array(
        self,
        rect_layers,
        text_layers,
        base_rect,
        shift_vectors,
        text="",
        text_size=1,
        text_angle=0,
    ):
        # manual, as in drawing individual rectangles and not using the gds array construct
        for rect in array_generator(base_rect, shift_vectors):
            for layer in rect_layers:
                self.add_rect(*layer, *rect)
            for layer in text_layers:
                (x1, y1), (x2, y2) = rect
                point = (x1 + x2) // 2, (y1 + y2) // 2
                self.add_text(*layer, point, text, text_size, text_angle)
