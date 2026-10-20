"""工作流行为测试：未审不得发布、版本绑定、断点恢复与增量保护。"""
import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/study-knowledge-base/scripts'))
import kb

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'batch';self.out=self.base/'out'
        kb.init(self.root,self.out,'set-logic','集合与逻辑')
        self.plan={'sources':[{'id':'s1','path':'source.txt','kind':'text','location':'教材第12页，第2段'}],'items':[{'id':'t1','kind':'topic','title':'集合','provenance':'original','state':'ready','source_ids':['s1']},{'id':'q1','kind':'question','title':'判断集合','provenance':'original','state':'ready','source_ids':['s1'],'statement':'statement.md','related':[{'id':'t1','reason':'用集合定义判断元素'}]}],'learning_order':['t1']}
        kb.write(self.root/'plan.json',self.plan)
        for name,body in {'source.txt':'原始材料','statement.md':r'题目 $1\in A$','drafts/t1/body.md':'定义与条件。','drafts/q1/answer.md':'解答。','drafts/q1/method.md':'方法。','evidence/review.md':'测试证据：由测试夹具模拟审查，不是学科验收。','evidence/visual.md':'测试模拟排版证据。'}.items():kb.write(self.root/name,body.encode())
        self.p=kb.Project(self.root);self.p.freeze()
    def approve(self,p=None):
        p=p or kb.Project(self.root);b=p.build()
        data={'revision':b['revision'],'items':[{'id':key,'decision':'pending' if i['state']=='pending' else 'approved','semantic_check':'passed','source_check':'matched','mode':'independent','reviewer':'test fixture','scope':'测试模拟完整范围','evidence':['evidence/review.md'],'next_action':'补充清晰来源'} for key,i in p.items.items()],'presentation':{'status':'passed','method':'test fixture','scope':'测试模拟','evidence':['evidence/visual.md']}}
        kb.write(p.root/'review.json',data);return data
    def test_idempotent_publish(self):
        self.approve();a=kb.Project(self.root).publish();b=kb.Project(self.root).publish()
        self.assertGreater(a['changed_files'],0);self.assertEqual(b['changed_files'],0)
        self.assertTrue((self.out/'笔记/t1.md').exists())
    def test_no_review(self):
        self.assertFalse(self.p.check()['ok'])
        with self.assertRaises(ValueError):self.p.publish()
    def test_changed_source_rejected(self):
        kb.write(self.root/'source.txt',b'changed')
        with self.assertRaises(ValueError):self.p.build()
    def test_changed_answer_invalidates_review(self):
        self.approve();kb.write(self.root/'drafts/q1/answer.md',b'new answer')
        self.assertFalse(kb.Project(self.root).check()['ok'])
    def test_warning_blocks_approved_review(self):
        kb.write(self.root/'drafts/q1/answer.md',b'$x=1,qquad y=2$');self.approve()
        self.assertFalse(kb.Project(self.root).check()['ok'])
    def test_local_link_rejected(self):
        kb.write(self.root/'drafts/q1/method.md',b'[wrong](../missing.md)');self.approve()
        self.assertFalse(kb.Project(self.root).check()['ok'])
    def test_missing_topic_not_silently_skipped(self):
        (self.root/'drafts/t1/body.md').unlink()
        with self.assertRaises(ValueError):self.p.build()
    def test_missing_visual_evidence(self):
        self.approve();(self.root/'evidence/visual.md').unlink()
        self.assertFalse(self.p.check()['ok'])
    def test_non_independent_rejected(self):
        d=self.approve();d['items'][0]['mode']='self';kb.write(self.root/'review.json',d)
        self.assertFalse(self.p.check()['ok'])
    def test_partial_review_rejected(self):
        d=self.approve();d['items'].pop();kb.write(self.root/'review.json',d)
        self.assertFalse(self.p.check()['ok'])
    def test_hand_edit_not_overwritten(self):
        self.approve();self.p.publish();kb.write(self.out/'笔记/t1.md',b'my edit')
        with self.assertRaises(ValueError):kb.Project(self.root).publish()
        self.assertEqual((self.out/'笔记/t1.md').read_bytes(),b'my edit')
    def test_crash_then_resume(self):
        self.approve();original=kb.write
        def fail_after_one(p,data):
            original(p,data)
            if p==self.out/'笔记/t1.md':raise OSError('simulated interruption')
        with patch.object(kb,'write',fail_after_one):
            with self.assertRaises(OSError):self.p.publish()
        done=kb.Project(self.root).publish();self.assertTrue(done['ok'])
        self.assertFalse(kb.read(self.out/'.kb/publish-journal.json')['remaining'])
    def test_pending_body_hidden(self):
        root=self.base/'pending';kb.init(root,self.out,'pending-case',None)
        plan={'sources':[{'id':'s2','path':'source.txt','kind':'text','location':'第1段'}],'items':[{'id':'q2','kind':'question','title':'未经核对的猜测标题','provenance':'original','state':'pending','reason':'缺来源','source_ids':['s2'],'statement':'raw.md'}],'learning_order':[]}
        kb.write(root/'plan.json',plan);kb.write(root/'source.txt',b'source');kb.write(root/'raw.md','错误转写不要展示'.encode())
        p=kb.Project(root);p.freeze();b=p.build()
        text=(Path(b['stage'])/'题/q2.md').read_text(encoding='utf-8')
        self.assertNotIn('错误转写',text);self.assertNotIn('猜测标题',text)
    def test_source_retained_without_visible_page_boilerplate(self):
        b=self.p.build();text=(Path(b['stage'])/'笔记/t1.md').read_text(encoding='utf-8')
        self.assertNotIn('第12页',text)
        self.assertNotIn('## 来源',text)
        self.assertTrue(list((Path(b['stage'])/'原始资料').glob('s1-*')))
        self.assertEqual(kb.read(self.root/'plan.json')['sources'][0]['location'],'教材第12页，第2段')
    def test_only_explicitly_selected_figure_is_displayed(self):
        for i in ['s2','s3']:
            self.plan['sources'].append({'id':i,'path':i+'.png','kind':'image','location':'原图位置'})
            kb.write(self.root/(i+'.png'),b'image fixture')
        self.plan['items'][0]['source_ids']+=['s2','s3']
        self.plan['items'][0]['display_source_ids']=['s2']
        kb.write(self.root/'plan.json',self.plan)
        # 计划变化采用新冻结状态，仅在独立测试夹具中重建。
        (self.root/'.kb/frozen.json').unlink()
        p=kb.Project(self.root);p.freeze();b=p.build()
        text=(Path(b['stage'])/'笔记/t1.md').read_text(encoding='utf-8')
        self.assertIn('s2-',text);self.assertNotIn('s3-',text)
        self.assertEqual(text.count('![]('),1)
        self.assertNotIn('来源身份',text)
    def test_invalid_display_source_is_rejected(self):
        self.plan['items'][0]['display_source_ids']=['s1']
        kb.write(self.root/'plan.json',self.plan)
        with self.assertRaises(ValueError):kb.Project(self.root)
    def test_new_batch_updates_owned_file_with_backup(self):
        self.approve();self.p.publish();root=self.base/'second';kb.init(root,self.out,'second',None)
        plan={'sources':[],'items':[{'id':'t1','kind':'topic','title':'集合','provenance':'authored','state':'ready','source_ids':[]}],'learning_order':['t1']}
        kb.write(root/'plan.json',plan);kb.write(root/'drafts/t1/body.md',b'updated content')
        for f in ['review.md','visual.md']:kb.write(root/'evidence'/f,b'evidence')
        p=kb.Project(root);p.freeze();d=self.approve(p);d['items'][0]['source_check']='not_applicable';kb.write(root/'review.json',d)
        self.assertTrue(p.publish()['ok']);self.assertTrue(list((self.out/'.kb/history').rglob('t1.md')))
    def test_source_and_item_ids_cannot_collide(self):
        self.plan['items'][0]['id']='s1';kb.write(self.root/'plan.json',self.plan)
        with self.assertRaises(ValueError):kb.Project(self.root)

    def test_partial_build_resumes_without_overwrite(self):
        b=self.p.build();stage=Path(b['stage']);(stage/'题/q1.md').unlink()
        self.p.build();self.assertTrue((stage/'题/q1.md').exists())
        kb.write(stage/'题/q1.md',b'edited')
        with self.assertRaises(ValueError):self.p.build()

    def test_pdf_only_question_rejected(self):
        self.plan['sources'][0]['kind']='pdf';kb.write(self.root/'plan.json',self.plan)
        with self.assertRaises(ValueError):kb.Project(self.root)

    def test_existing_reference_is_verified(self):
        self.approve();self.p.publish()
        root=self.base/'ref';kb.init(root,self.out,'ref',None)
        kb.write(root/'plan.json',{'sources':[],'items':[{'id':'t2','kind':'topic','title':'扩展','provenance':'authored','state':'ready','source_ids':[],'related':[{'id':'t1','reason':'以集合为前置'}]}],'learning_order':['t2']})
        kb.write(root/'drafts/t2/body.md',b'new');p=kb.Project(root);p.freeze();b=p.build()
        self.assertIn('t1',b['external'])
        kb.write(self.out/'笔记/t1.md',b'manual change')
        with self.assertRaises(ValueError):kb.Project(root).build()

if __name__=='__main__':unittest.main()
