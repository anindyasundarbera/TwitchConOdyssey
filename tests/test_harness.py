import json
import unittest
from pathlib import Path
from harness.run import select_task
from schemas.validate import contract

class HarnessTests(unittest.TestCase):
    def test_dependency_selection(self):
        tasks=[{'id':'b','status':'todo','depends':['a']},{'id':'a','status':'todo','depends':[]}]
        self.assertEqual(select_task(tasks)['id'],'a')
        tasks[1]['status']='done'
        self.assertEqual(select_task(tasks)['id'],'b')
    def test_control_schema_rejects_drift(self):
        good={'version':1,'tasks':[{'id':'T1','objective':'test','status':'done','depends':[],'requirements':['R01'],'validation':['test command']}]}
        contract('tasks',good)
        good['tasks'][0]['status']='probably done'
        with self.assertRaises(ValueError):contract('tasks',good)
    def test_claims_have_test_mappings(self):
        data=json.loads(Path('harness/requirements.json').read_text())
        contract('requirements',data)
        self.assertEqual(len(data['requirements']),8)
        for row in data['requirements']:
            self.assertTrue(row['tests']);self.assertTrue(row['threshold'])
