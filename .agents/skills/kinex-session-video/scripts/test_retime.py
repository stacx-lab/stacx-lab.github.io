"""Clock-map invariants; no robot, recordings, browser, or encoder required."""
import copy
import unittest
from PIL import ImageFont
from render_video import compile_events, compile_retime, scene_clock, SANS, BOLD, MONO, MONO_BOLD
from session_source import run_metadata


class RetimeTests(unittest.TestCase):
    def event(self):
        return dict(entry=0, duration=4., sim_start=10., sim_end=14., retime=dict(
            typing_s=.4, result_hold_s=.6, segments=[
                dict(end_source_s=11., speed=.5, reason='Contact'),
                dict(end_source_s='end', speed=3., reason='Withdraw')]))

    def test_slow_contact_then_fast_withdrawal(self):
        event = self.event(); compile_retime(event)
        self.assertEqual(scene_clock(event, 0), (10., 0.))
        self.assertEqual(scene_clock(event, 1.4), (10.5, .5))
        clock, speed = scene_clock(event, 2.9)
        self.assertAlmostEqual(clock, 12.5); self.assertEqual(speed, 3.)
        self.assertEqual(scene_clock(event, 4), (14., 0.))

    def test_continuity_and_result_boundary(self):
        event = self.event(); compile_retime(event)
        times = [scene_clock(event, i/1000)[0] for i in range(4001)]
        self.assertTrue(all(b >= a for a, b in zip(times, times[1:])))
        end = event['result_fraction'] * event['duration']
        self.assertAlmostEqual(end, 3.4)
        self.assertLess(scene_clock(event, end - .001)[0], 14.)
        self.assertAlmostEqual(scene_clock(event, end)[0], 14.)
        for knot in event['motion_keyframes']:
            self.assertAlmostEqual(scene_clock(event, knot['at_s'])[0], knot['source_s'])

    def test_bad_plans_fail(self):
        valid = self.event()
        for field, value in [('speed', 0.), ('speed', -1.), ('speed', float('nan')), ('end_source_s', 16.), ('end_source_s', 9.)]:
            event = copy.deepcopy(valid); event['retime']['segments'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                compile_retime(event)
        event = self.event(); event['duration'] = 5.
        with self.assertRaises(ValueError): compile_retime(event)
        event = self.event(); event['retime']['segments'][-1]['end_source_s'] = 13.
        with self.assertRaises(ValueError): compile_retime(event)

    def test_speed_ramps_preserve_endpoints_and_report_true_speed(self):
        event = dict(entry=0, duration=3., sim_start=0., sim_end=4., retime=dict(
            typing_s=.5, result_hold_s=.5, segments=[
                dict(end_source_s=2., speed=2., start_speed=0., end_speed=4., reason='Accelerate'),
                dict(end_source_s='end', speed=2., start_speed=4., end_speed=0., reason='Decelerate')]))
        compile_retime(event)
        self.assertEqual(scene_clock(event, .5), (0., 0.))
        self.assertEqual(scene_clock(event, 1.), (.5, 2.))
        self.assertEqual(scene_clock(event, 1.5), (2., 4.))
        self.assertEqual(scene_clock(event, 2.), (3.5, 2.))
        self.assertEqual(scene_clock(event, 2.5), (4., 0.))
        for i in range(1, 2000):
            t = .5 + i / 1000
            derivative = (scene_clock(event, t + 1e-6)[0] - scene_clock(event, t - 1e-6)[0]) / 2e-6
            self.assertAlmostEqual(derivative, scene_clock(event, t)[1], places=5)
        for change in [{'start_speed': -1}, {'end_speed': float('nan')}, {'speed': 3}]:
            bad = copy.deepcopy(event); bad['retime']['segments'][0].update(change)
            with self.assertRaises(ValueError): compile_retime(bad)

    def test_no_speed_plan_and_stationary_observation(self):
        for end in [10., 14.]:
            event = dict(entry=0, duration=4., sim_start=10., sim_end=end)
            compile_retime(event)
            self.assertEqual(scene_clock(event, 0), (10., 0.))
            self.assertEqual(scene_clock(event, 4), (end, 0.))
        event['typing_fraction'] = .8
        with self.assertRaises(ValueError): compile_retime(event)

    def test_exact_bundled_font_families(self):
        for path, family in [(SANS, 'Lato'), (BOLD, 'Lato'), (MONO, 'CommitMono'), (MONO_BOLD, 'CommitMono')]:
            self.assertTrue(path.is_file())
            self.assertEqual(ImageFont.truetype(path, 17).getname()[0].replace(' ', ''), family)

    def source_and_edit(self):
        def entry(index, role, content, **extra):
            return dict(id=str(index), timestamp='2026-01-01T00:00:00Z',
                        message=dict(role=role, content=content, **extra))
        entries = [entry(0, 'user', [dict(type='text', text='Hang the mug')])]
        for index, clock in [(1, 4), (3, 10)]:
            entries.append(entry(index, 'assistant', [dict(type='toolCall', id=str(index),
                name='closed_loop', arguments=dict(control=dict(python='return move()')))]))
            entries.append(entry(index + 1, 'toolResult', [dict(type='text', text='{"time_s":%s}' % clock)], toolCallId=str(index)))
        source = dict(entries=entries, results={str(i): (i + 1, entries[i + 1]) for i in [1, 3]},
                      images={}, frames=[dict(source_time_s=0), dict(source_time_s=10)])
        edit = dict(duration=3, from_start=True, continuous_source=True, events=[
            dict(entry=0, kind='user', duration=1),
            dict(entry=1, duration=1), dict(entry=3, duration=1)])
        return source, edit

    def test_first_task_and_continuous_coverage(self):
        source, edit = self.source_and_edit()
        events = compile_events(source, edit)
        self.assertEqual([(e['sim_start'], e['sim_end']) for e in events], [(0, 0), (0, 4), (4, 10)])
        # Merely beginning with a tool at time zero loses the original task.
        late = copy.deepcopy(edit); late['events'].pop(0); late['duration'] = 2
        with self.assertRaisesRegex(ValueError, 'first user task'):
            compile_events(source, late)
        # An intro followed by a later successful motion still omits source time.
        gap = copy.deepcopy(edit); gap['events'].pop(1); gap['duration'] = 2
        with self.assertRaisesRegex(ValueError, 'omit source time'):
            compile_events(source, gap)

    def test_code_excerpts_are_evidence_linked(self):
        source, edit = self.source_and_edit()
        edit['events'][1].update(code_field='control.python', code_excerpt='move()')
        self.assertEqual(compile_events(source, edit)[1]['body'], 'move()')
        edit['events'][1]['code_excerpt'] = 'invented_move()'
        with self.assertRaisesRegex(ValueError, 'verbatim'):
            compile_events(source, edit)
        edit['events'][1].update(code_excerpt='move()', end_clock_entry=4,
            following_calls=[dict(entry=3, code_field='control.python', code_excerpt='fabricated()')])
        edit['events'].pop(); edit['duration'] = 2
        with self.assertRaisesRegex(ValueError, 'verbatim'):
            compile_events(source, edit)

    def test_recorded_model_and_effort_changes(self):
        entries = [
            dict(type='model_change', modelId='initial-model'),
            dict(type='thinking_level_change', thinkingLevel='medium'),
            dict(type='model_change', modelId='run-model'),
            dict(type='thinking_level_change', thinkingLevel='high'),
            dict(message=dict(role='user', content=[])),
            dict(message=dict(role='assistant', model='run-model', thinkingLevel='high')),
            dict(message=dict(role='assistant', model='other-model', thinkingLevel='low')),
        ]
        resolved = run_metadata(dict(entries=entries))
        self.assertEqual(resolved[0], dict(model='initial-model', effort=None))
        self.assertEqual(resolved[4], dict(model='run-model', effort='high'))
        self.assertEqual(resolved[5], dict(model='run-model', effort='high'))
        self.assertEqual(resolved[6], dict(model='other-model', effort='low'))
        self.assertEqual(run_metadata(dict(entries=[dict(message=dict(role='user'))]))[0],
                         dict(model=None, effort=None))


if __name__ == '__main__':
    unittest.main()
