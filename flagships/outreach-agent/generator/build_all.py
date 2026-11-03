import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from wf_99_01 import build_99, build_01, build_00
from wf_02 import build_02
from wf_03 import build_03
from wf_04 import build_04
from wf_05 import build_05
from wf_06 import build_06
import os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'workflows')
os.makedirs(D, exist_ok=True)
build_99(f'{D}/OA-99-error-handler.json'); build_01(f'{D}/OA-01-intake.json'); build_00(f'{D}/OA-00-form-intake.json'); build_02(f'{D}/OA-02-research-draft.json')
build_03(f'{D}/OA-03-approval-send.json'); build_04(f'{D}/OA-04-followups.json'); build_05(f'{D}/OA-05-inbox-agent.json'); build_06(f'{D}/OA-06-weekly-report.json')
print(sorted(os.listdir(D)))
