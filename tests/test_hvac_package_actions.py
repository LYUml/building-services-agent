import unittest
from bsa.adpi_screen import screen
from bsa.hvac_package import review_actions


class PackageActionTests(unittest.TestCase):
    def review(self,ratio=2,load=100,verified=True):
        return screen(dict(terminals=[dict(id='T1',directions=dict(east=dict(cases={
            name:dict(ratio=ratio,status='within_catalogue') for name in ('maximum','minimum')})))]),
            criterion=dict(source='Synthetic test source',room_load_range_W_m2=[35,160],ratio_range=[1,3.4]),
            room_load_W_m2=load,facts={name:verified for name in (
                'room_load_verified','product_category_verified','lengths_verified','installation_verified','edition_selected')})

    def test_pending_requests_preserve_load_conflict_without_ratio_failure(self):
        r=self.review(ratio=4,load=170.1,verified=None)
        actions=review_actions({'adpi_review':r},{})
        self.assertEqual(len(actions),6)
        self.assertTrue(all(x['stage']=='adpi_review' for x in actions))
        self.assertEqual(actions[-1]['supplied_load_W_m2'],170.1)
        self.assertNotIn('terminal_ratio_screen_failed',[x['code'] for x in actions])
        self.assertNotIn('stage',r['data_requests'][0])

    def test_eligible_failure_identifies_both_operating_cases(self):
        actions=review_actions({'adpi_review':self.review(ratio=4)},{})
        self.assertEqual(len(actions),1)
        self.assertEqual(actions[0]['code'],'terminal_ratio_screen_failed')
        self.assertEqual({x['case'] for x in actions[0]['cases']},{'maximum','minimum'})
        self.assertTrue(all(x['terminal']=='T1' for x in actions[0]['cases']))

    def test_error_omission_and_scoped_success(self):
        self.assertEqual(review_actions({},{}),[])
        self.assertEqual(review_actions({'adpi_review':self.review()},{}),[])
        actions=review_actions({},dict(adpi_review='Controlled source mismatch'))
        self.assertEqual(actions[0]['code'],'stage_execution_error')
        self.assertEqual(actions[0]['detail'],'Controlled source mismatch')
