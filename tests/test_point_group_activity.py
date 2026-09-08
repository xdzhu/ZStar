from pathlib import Path
import tempfile
import unittest

from zstar import group_modesDB
from zstar.read_irrep import UNRESOLVED_IRREP, analyze_irreps, build_mode_active_info_from_db


# Offline reference snapshot transcribed from the Bilbao POINT tables. IR
# species are taken from V and static Raman species from the symmetric square
# [V^2]. Conjugate 1E/2E pairs use the conventional real E notation.
REFERENCE_ACTIVITY_TABLE = """
1;A;A;A
-1;Au;Ag;Ag,Au
2;A,B;A,B;A,B
m;A',A'';A',A'';A',A''
2/m;Au,Bu;Ag,Bg;Ag,Au,Bg,Bu
222;B1,B2,B3;A,B1,B2,B3;A,B1,B2,B3
mm2;A1,B1,B2;A1,A2,B1,B2;A1,A2,B1,B2
mmm;B1u,B2u,B3u;Ag,B1g,B2g,B3g;Ag,Au,B1g,B1u,B2g,B2u,B3g,B3u
4;A,E;A,B,E;A,B,E
-4;B,E;A,B,E;A,B,E
4/m;Au,Eu;Ag,Bg,Eg;Ag,Au,Bg,Bu,Eg,Eu
422;A2,E;A1,B1,B2,E;A1,A2,B1,B2,E
4mm;A1,E;A1,B1,B2,E;A1,A2,B1,B2,E
-42m;B2,E;A1,B1,B2,E;A1,A2,B1,B2,E
4/mmm;A2u,Eu;A1g,B1g,B2g,Eg;A1g,A1u,A2g,A2u,B1g,B1u,B2g,B2u,Eg,Eu
3;A,E;A,E;A,E
-3;Au,Eu;Ag,Eg;Ag,Au,Eg,Eu
32;A2,E;A1,E;A1,A2,E
3m;A1,E;A1,E;A1,A2,E
-3m;A2u,Eu;A1g,Eg;A1g,A1u,A2g,A2u,Eg,Eu
6;A,E1;A,E1,E2;A,B,E1,E2
-6;A'',E';A',E',E'';A',A'',E',E''
6/m;Au,E1u;Ag,E1g,E2g;Ag,Au,Bg,Bu,E1g,E1u,E2g,E2u
622;A2,E1;A1,E1,E2;A1,A2,B1,B2,E1,E2
6mm;A1,E1;A1,E1,E2;A1,A2,B1,B2,E1,E2
-6m2;A2'',E';A1',E',E'';A1',A1'',A2',A2'',E',E''
6/mmm;A2u,E1u;A1g,E1g,E2g;A1g,A1u,A2g,A2u,B1g,B1u,B2g,B2u,E1g,E1u,E2g,E2u
23;T;A,E,T;A,E,T
m-3;Tu;Ag,Eg,Tg;Ag,Au,Eg,Eu,Tg,Tu
432;T1;A1,E,T2;A1,A2,E,T1,T2
-43m;T2;A1,E,T2;A1,A2,E,T1,T2
m-3m;T1u;A1g,Eg,T2g;A1g,A1u,A2g,A2u,Eg,Eu,T1g,T2g,T1u,T2u
""".strip()


def _parse_reference_table():
    expected = {}
    for line in REFERENCE_ACTIVITY_TABLE.splitlines():
        point_group, ir, raman, all_irreps = line.split(";")
        expected[point_group] = {
            "ir": ir.split(","),
            "raman": raman.split(","),
            "all": all_irreps.split(","),
        }
    return expected


class PointGroupActivityTests(unittest.TestCase):
    def test_all_32_crystallographic_point_groups_match_reference(self):
        expected = _parse_reference_table()
        self.assertEqual(len(expected), 32)
        self.assertEqual(set(group_modesDB.list_supported_point_groups()), set(expected))
        for point_group, reference in expected.items():
            with self.subTest(point_group=point_group):
                self.assertEqual(group_modesDB.describe_point_group(point_group), reference)

    def test_full_irrep_set_retains_genuinely_silent_species(self):
        activity = build_mode_active_info_from_db("m-3m")
        self.assertEqual(activity["IR"], {"T1u"})
        self.assertEqual(activity["Raman"], {"A1g", "Eg", "T2g"})
        self.assertIn("A2u", activity["Silent"])
        self.assertIn("T1g", activity["Silent"])

    def test_null_phonopy_label_is_unresolved_not_silent(self):
        content = """\
point_group: mmm
normal_modes:
- band_indices: [1, 2, 3]
  frequency: 0.0
  ir_label: null
- band_indices: [4]
  frequency: 2.0
  ir_label: null
- band_indices: [5]
  frequency: 3.0
  ir_label: Au
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "irreps.yaml"
            path.write_text(content, encoding="utf-8")
            result = analyze_irreps(path)

        self.assertEqual(result["Acoustic"][UNRESOLVED_IRREP], [1, 2, 3])
        self.assertEqual(result["Unresolved"][UNRESOLVED_IRREP], [4])
        self.assertNotIn(UNRESOLVED_IRREP, result["Silent"])
        self.assertEqual(result["Silent"]["Au"], [5])

    def test_reference_metadata_is_exposed(self):
        self.assertEqual(
            group_modesDB.ACTIVITY_REFERENCE_DOI,
            "10.1107/S0108767305040286",
        )
        self.assertEqual(
            group_modesDB.ACTIVITY_REFERENCE_URL,
            "https://www.cryst.ehu.eus/rep/point.html",
        )


if __name__ == "__main__":
    unittest.main()
