import json
import tempfile
import unittest
from pathlib import Path

from indexer.parallel_analysis import analyze_parallel, scan_fortran, scan_c, Guards
from indexer.graph_builder import build_graph


class ParallelAnalysisTests(unittest.TestCase):
    def test_omp_continuations_and_join_keep_lines_and_enclosed_calls(self):
        text = 'SUBROUTINE step\n!$OMP PARALLEL DO &\n!$OMP PRIVATE(i)\nDO i=1,n\nCALL work( &\n a,b)\nENDDO\n!$OMP END PARALLEL DO\nEND SUBROUTINE\n'
        events, issues = scan_fortran(text, 'dyn_em/test.F')
        region, call, join = events
        self.assertEqual(region['directive'], 'PARALLEL DO PRIVATE(i)')
        self.assertEqual(region['evidence'][0]['endLine'], 3)
        self.assertEqual(call['evidence'][0]['startLine'], 5)
        self.assertEqual(call['evidence'][0]['endLine'], 6)
        self.assertEqual(call['threadContext'], 'parallel do')
        self.assertEqual(join['kind'], 'omp_join')
        self.assertEqual(join['regionId'], region['id'])
        self.assertEqual(join['evidence'][0]['startLine'], 8)
        self.assertFalse(issues)

    def test_nowait_master_and_critical_do_not_become_barriers(self):
        events, _ = scan_fortran('SUBROUTINE step\n!$OMP PARALLEL\n!$OMP DO\n!$OMP END DO NOWAIT\n!$OMP MASTER\n!$OMP END MASTER\n!$OMP CRITICAL\n!$OMP END CRITICAL\n!$OMP END PARALLEL\nEND SUBROUTINE', 'dyn_em/test.F')
        ends = [event for event in events if event['operation'].startswith('END')]
        self.assertEqual([event['kind'] for event in ends], ['omp_end', 'omp_end', 'omp_end', 'omp_join'])

    def test_preprocessor_alternatives_and_runtime_conditions_are_retained(self):
        text = 'SUBROUTINE step\n#ifdef DM_PARALLEL\nIF (active) THEN\nCALL MPI_Barrier(comm,ierr)\nENDIF\n#else\nCALL fallback()\n#endif\nEND SUBROUTINE'
        events, _ = scan_fortran(text, 'dyn_em/test.F')
        self.assertEqual(events[0]['guards'], ['defined(DM_PARALLEL)'])
        self.assertEqual(events[0]['conditions'], ['IF (active) THEN'])
        self.assertEqual(events[1]['guards'], ['!((defined(DM_PARALLEL)))'])
        self.assertEqual(events[1]['conditions'], [])

    def test_comments_strings_and_unmatched_omp_are_not_execution_evidence(self):
        events, issues = scan_fortran('SUBROUTINE step\n! CALL MPI_WAIT(req,s,i)\nPRINT *, "CALL MPI_BARRIER(comm,i)"\n!$OMP END PARALLEL\nEND SUBROUTINE', 'dyn_em/test.F')
        self.assertFalse(events)
        self.assertEqual(len(issues), 1)

    def test_c_multiline_requests_guards_and_neighbor_conditions(self):
        text = '''// MPI_Barrier(fake);
void exch(int n) {
#ifndef STUBMPI
  puts("MPI_Wait(fake)");
  if (n > 1) {
    MPI_Irecv(buf, size, MPI_CHAR,
              peer, tag, comm, &recv);
    if (peer != MPI_PROC_NULL) { MPI_Wait(&recv, &stat); }
  }
#endif
}'''
        events, issues = scan_c(text, 'external/RSL_LITE/test.c')
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['scope'], 'exch')
        self.assertEqual(events[0]['arguments'][-1], '&recv')
        self.assertEqual(events[0]['evidence'][0]['endLine'], 7)
        self.assertEqual(events[1]['guards'], ['!defined(STUBMPI)'])
        self.assertEqual(events[1]['kind'], 'mpi_wait')
        self.assertEqual(len(events[1]['conditions']), 2)
        self.assertFalse(issues)

    def test_registry_include_membership_and_deterministic_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Registry').mkdir()
            (root / 'dyn_em').mkdir()
            (root / 'Registry/Registry.EM').write_text('include Registry.EM_COMMON\n')
            (root / 'Registry/Registry.EM_COMMON').write_text('halo HALO_TEST dyn_em 8:u,v;4:mu\n')
            (root / 'Registry/not_active').write_text('halo UNUSED dyn_em 8:fake\n')
            (root / 'dyn_em/solve.F').write_text('SUBROUTINE step\n#ifdef DM_PARALLEL\n#include "HALO_TEST.inc"\n#endif\nEND SUBROUTINE\n')
            result = analyze_parallel(root, {'commit': 'test'})
            self.assertEqual(len(result['communications']), 1)
            self.assertEqual(result['communications'][0]['groups'][1]['fields'], ['mu'])
            self.assertEqual(result['events'][0]['communicationId'], 'HALO_TEST')
            self.assertEqual(result, analyze_parallel(root, {'commit': 'test'}))
            self.assertNotIn(directory, json.dumps(result))

    def test_cpp_elif_excludes_all_prior_branches(self):
        guards = Guards()
        guards.update('#if A')
        guards.update('#elif B')
        self.assertEqual(guards.values(), ['!((A)) && (B)'])
        guards.update('#else')
        self.assertEqual(guards.values(), ['!((A) || (B))'])

    def test_normal_graph_indexing_writes_a_matching_parallel_companion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            (root / 'Registry').mkdir(parents=True)
            (root / 'dyn_em').mkdir()
            (root / 'Registry/Registry.EM').write_text('halo HALO_TEST dyn_em 8:u,v\n')
            (root / 'dyn_em/solve_em.F').write_text('SUBROUTINE solve_em\n!$OMP PARALLEL DO\nDO i=1,n\nCALL work(i)\nENDDO\n!$OMP END PARALLEL DO\nEND SUBROUTINE\n')
            target = Path(directory) / 'output/graph.json'
            build_graph(str(root), str(target), {'source_id': 'fixture'})
            graph = json.loads(target.read_text(encoding='utf-8'))
            parallel = json.loads(target.with_suffix('.parallel.json').read_text(encoding='utf-8'))
            self.assertEqual(parallel['metadata']['indexed_at'], graph['metadata']['indexed_at'])
            self.assertEqual(parallel['metadata']['source_id'], 'fixture')
            self.assertTrue(any(event['kind'] == 'omp_join' for event in parallel['events']))

    def test_actual_snapshots_resolve_solver_halo_and_c_waits_without_global_barrier_claim(self):
        snapshots = Path(__file__).resolve().parents[1] / 'public/data/snapshots'
        for version in ('wrf-v4.7.1', 'wrf-v4.8.0'):
            with self.subTest(version=version):
                index = json.loads((snapshots / f'{version}.parallel.json').read_text())
                graph = json.loads((snapshots / f'{version}.json').read_text())
                self.assertEqual(index['metadata']['commit'], graph['metadata']['commit'])
                self.assertEqual(index['metadata']['indexed_at'], graph['metadata']['indexed_at'])
                self.assertIsNone(index['metadata']['source_root'])
                solver = [event for event in index['events'] if event['scope'] == 'solve_em']
                self.assertTrue(any(event.get('communicationId') == 'HALO_EM_A' for event in solver))
                self.assertTrue(any(event['kind'] == 'omp_join' for event in solver))
                waits = [event for event in index['events'] if event['scope'] == 'rsl_lite_exch_y' and event['kind'] == 'mpi_wait']
                self.assertEqual(len(waits), 4)
                self.assertTrue(all(event['conditions'] and event['arguments'] for event in waits))
                self.assertTrue(index['generatorEvidence'])


if __name__ == '__main__':
    unittest.main()
