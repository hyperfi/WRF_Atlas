import tempfile
import unittest
from pathlib import Path

from indexer.fortran_parser import parse_fortran_file, preprocess_lines, direct_argument_name
from indexer.graph_builder import KnowledgeGraph, _link_execution_phases_from_calls
from indexer.registry_parser import parse_registry


class FortranParserTests(unittest.TestCase):
    def test_multiline_call_preserves_source_range(self):
        lines = [
            "  CALL lsm(a, &\n",
            "         & b, &\n",
            "         & c)\n",
        ]

        logical = preprocess_lines(lines, "driver.F")

        self.assertEqual(len(logical), 1)
        self.assertEqual(logical[0].start_line, 1)
        self.assertEqual(logical[0].end_line, 3)
        self.assertIn("CALL lsm", logical[0].text)

    def test_select_case_records_symbolic_dispatch_and_call_evidence(self):
        source = """\
MODULE example_driver
CONTAINS
SUBROUTINE surface_driver(config_flags)
  SELECT CASE (config_flags%sf_surface_physics)
  CASE (LSMSCHEME)
    CALL lsm(a, &
             b)
  END SELECT
END SUBROUTINE surface_driver
END MODULE example_driver
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "module_surface_driver.F"
            path.write_text(source, encoding="utf-8")
            result = parse_fortran_file(str(path))

        call = next(item for item in result["calls"] if item["subroutine"] == "lsm")
        self.assertEqual(call["caller"], "surface_driver")
        self.assertEqual(call["caller_type"], "subroutine")
        self.assertEqual(call["dispatch_var"], "sf_surface_physics")
        self.assertEqual(call["dispatch_value"], "LSMSCHEME")
        self.assertEqual(call["line"], 6)
        self.assertEqual(call["end_line"], 7)

    def test_program_calls_keep_program_scope(self):
        source = """\
PROGRAM wrf
  CALL wrf_init()
END PROGRAM wrf
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "wrf.F90"
            path.write_text(source, encoding="utf-8")
            result = parse_fortran_file(str(path))

        self.assertEqual(result["calls"][0]["caller"], "wrf")
        self.assertEqual(result["calls"][0]["caller_type"], "program")

    def test_call_words_inside_debug_strings_are_not_edges(self):
        source = """\
SUBROUTINE first_rk_step_part1()
  CALL wrf_debug(200, ' call radiation_driver')
  CALL radiation_driver(a)
END SUBROUTINE first_rk_step_part1
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "module_first_rk_step_part1.F90"
            path.write_text(source, encoding="utf-8")
            result = parse_fortran_file(str(path))

        targets = [call["subroutine"] for call in result["calls"]]
        self.assertEqual(targets, ["wrf_debug", "radiation_driver"])
        radiation_call = result["calls"][1]
        self.assertEqual(radiation_call["line"], 3)

    def test_call_arguments_keep_nested_commas_and_reject_expressions(self):
        source = """\
SUBROUTINE surface_driver()
  CALL lsm(grid%hfx, tsk(i,j), label='rain, snow', value=max(a,b), qfx + 1)
END SUBROUTINE surface_driver
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "driver.F"
            path.write_text(source, encoding="utf-8")
            call = parse_fortran_file(str(path))["calls"][0]

        self.assertEqual(call["arguments"], [
            "grid%hfx", "tsk(i,j)", "label='rain, snow'", "value=max(a,b)", "qfx + 1"
        ])
        self.assertEqual(direct_argument_name(call["arguments"][0]), "hfx")
        self.assertEqual(direct_argument_name(call["arguments"][1]), "tsk")
        # Syntax alone cannot distinguish an array reference from a function;
        # the graph builder additionally requires a Registry state-name match.
        self.assertEqual(direct_argument_name(call["arguments"][3]), "max")
        self.assertIsNone(direct_argument_name(call["arguments"][4]))

    def test_physics_suite_setting_keeps_override_condition_and_line(self):
        source = """\
MODULE checks
CONTAINS
SUBROUTINE setup_physics_suite
  SELECT CASE (trim(physics_suite_lowercase))
  CASE ('conus')
    IF (model_config_rec % mp_physics(i) == -1) model_config_rec % mp_physics(i) = THOMPSON
  END SELECT
END SUBROUTINE setup_physics_suite
END MODULE checks
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "checks.F"
            path.write_text(source, encoding="utf-8")
            settings = parse_fortran_file(str(path))["physics_suites"]

        self.assertEqual(settings, [{
            "suite": "conus", "option": "mp_physics", "constant": "thompson",
            "line": 6, "end_line": 6,
        }])

    def test_two_option_physics_requirement_preserves_source_condition(self):
        source = """\
SUBROUTINE check_nml()
 IF ((model_config_rec%bl_pbl_physics(i) .EQ. TEMFPBLSCHEME) .AND. &
     (model_config_rec%sf_sfclay_physics(i) .NE. TEMFSFCSCHEME)) THEN
   count_fatal_error = count_fatal_error + 1
 END IF
END SUBROUTINE check_nml
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "checks.F"
            path.write_text(source, encoding="utf-8")
            rules = parse_fortran_file(str(path))["physics_constraints"]

        self.assertEqual(rules, [{
            "source_option": "bl_pbl_physics", "source_constant": "temfpblscheme",
            "required_option": "sf_sfclay_physics", "required_constant": "temfsfcscheme",
            "line": 2, "end_line": 3,
        }])


class RegistryParserTests(unittest.TestCase):
    def test_package_keeps_its_actual_file_and_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / "Registry"
            registry_dir.mkdir()
            registry_file = registry_dir / "Registry.TEST"
            registry_file.write_text(
                "# fixture\n\npackage lsmscheme sf_surface_physics==2 - state:smcrel\n",
                encoding="utf-8",
            )

            result = parse_registry(temp_dir, ["Registry/Registry.TEST"])

        self.assertEqual(len(result["packages"]), 1)
        package = result["packages"][0]
        self.assertEqual(package["package_name"], "lsmscheme")
        self.assertEqual(package["source_file"], str(Path("Registry") / "Registry.TEST"))
        self.assertEqual(package["source_line"], 3)


class ExecutionGraphTests(unittest.TestCase):
    def test_phase_edges_require_and_preserve_exact_call_evidence(self):
        graph = KnowledgeGraph()
        graph.add_edge(
            "subroutine:first_rk_step_part1",
            "subroutine:radiation_driver",
            "CALLS",
            {
                "confidence": "exact",
                "evidence": [{"path": "dyn_em/module_first_rk_step_part1.F", "startLine": 264}],
            },
        )

        _link_execution_phases_from_calls(graph)

        phase_edges = [edge for edge in graph.edges if edge["type"] == "EXECUTES_DURING"]
        self.assertEqual(len(phase_edges), 1)
        self.assertEqual(phase_edges[0]["source"], "subroutine:radiation_driver")
        self.assertEqual(phase_edges[0]["data"]["confidence"], "exact")
        self.assertEqual(phase_edges[0]["data"]["evidence"][0]["startLine"], 264)


if __name__ == "__main__":
    unittest.main()
