"""可恢复的知识库批处理：冻结来源、构建草稿、审查门禁、增量发布。Python标准库。"""
import argparse, contextlib, hashlib, json, os, re, shutil, sys, tempfile
from pathlib import Path
import check_markdown, check_tex_hygiene, check_fragments

VERSION = '1.1'
KINDS = {'topic': '笔记', 'question': '题', 'tip': '技巧'}

def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(p): return sha(p.read_bytes())
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def nonempty(x): return isinstance(x,str) and bool(x.strip())
def need(ok,message):
    if not ok: raise ValueError(message)

def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=data if isinstance(data,bytes) else (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    fd,tmp=tempfile.mkstemp(prefix='.kb-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw)
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def child(root,name):
    need(nonempty(name),'缺少相对路径')
    p=(root/name).resolve()
    need(p.is_relative_to(root.resolve()) and p!=root.resolve(),'路径超出工作目录：'+name)
    return p

def safe_id(value):
    need(isinstance(value,str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',value),'id须为简短字母数字、下划线或连字符')
    need(value.upper() not in {'CON','PRN','AUX','NUL',*[f'{s}{n}' for s in ['COM','LPT'] for n in range(1,10)]},'不支持的文件名')
    return value

@contextlib.contextmanager
def mutex(root):
    root.mkdir(parents=True,exist_ok=True)
    f=(root/'.publish.lock').open('a+b');f.seek(0)
    if not f.read(1):f.write(b'0');f.flush()
    f.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:f.close()

class Project:
    def __init__(self,root):
        self.root=Path(root).resolve();self.config=read(self.root/'project.json');self.plan=read(self.root/'plan.json')
        need(self.config.get('version')==1,'配置version必须为1')
        safe_id(self.config.get('batch_id'))
        need(nonempty(self.config.get('output_dir')),'配置缺output_dir')
        self.output=(self.root/self.config['output_dir']).resolve()
        need(not self.output.is_relative_to(self.root), '发布目录应在批次工作目录之外，避免递归输入/输出')
        self.state=self.root/'.kb';self.state.mkdir(exist_ok=True)
        self.sources={};self.items={}
        for field,target in [('sources',self.sources),('items',self.items)]:
            need(isinstance(self.plan.get(field),list),'plan缺少'+field+'数组')
            for item in self.plan[field]:
                key=safe_id(item.get('id'));need(key.lower() not in [k.lower() for k in target],'重复id：'+key);target[key]=item
        need(bool(self.items),'items不能为空，先声明完整批次范围')
        for key,s in self.sources.items():
            need(nonempty(s.get('path')) and nonempty(s.get('location')),'来源缺路径或位置：'+key)
            need(s.get('kind') in ['image','text','pdf','transcript'],'无效来源类型：'+key)
        for key,item in self.items.items():
            need(item.get('kind') in KINDS,'无效条目类型：'+key)
            need(nonempty(item.get('title')) and '\n' not in item['title'],'缺少单行自然标题：'+key)
            need(item.get('provenance') in ['original','authored'],'缺provenance：'+key)
            need(item.get('state') in ['ready','pending'],'state须为ready或pending：'+key)
            refs=item.get('source_ids');need(isinstance(refs,list) and all(x in self.sources for x in refs),'来源id缺失：'+key)
            display=item.get('display_source_ids',[])
            need(isinstance(display,list) and all(isinstance(x,str) for x in display) and len(display)==len(set(display)) and all(x in refs and self.sources[x]['kind']=='image' for x in display),'display_source_ids须为来源中的不重复局部图id：'+key)
            need(item['provenance']=='authored' or bool(refs),'来源派生条目不能没有来源：'+key)
            if item['state']=='pending':need(nonempty(item.get('reason')),'待核项必须说明下一步缺什么：'+key)
            if item['kind']=='question' and item['state']=='ready':need(nonempty(item.get('statement')),'题目须指定冻结题干文件：'+key)
            if item['kind']=='question' and item['state']=='ready' and item['provenance']=='original':
                need(any(self.sources[x]['kind']!='pdf' for x in refs),'题目不能只挂整本PDF：请提供逐题裁图或独立文本来源单元：'+key)
        self.catalog=read(self.output/'.kb/catalog.json') if (self.output/'.kb/catalog.json').exists() else {'cards':{},'files':{}}
        need(not set(self.items)&set(self.sources),'条目和来源id应区分，避免混淆')

    def source_path(self,s):
        p=(self.root/s['path']).resolve();need(p.is_file() and p.stat().st_size,'来源不存在或为空：'+str(p));return p

    def snapshot(self):
        hashes={'project.json':file_sha(self.root/'project.json'),'plan.json':file_sha(self.root/'plan.json')}
        for key,s in self.sources.items():hashes['source:'+key]=file_sha(self.source_path(s))
        for key,item in self.items.items():
            if item.get('statement'):
                p=child(self.root,item['statement']);need(p.is_file(),'缺题干：'+key);hashes['statement:'+key]=file_sha(p)
        return hashes

    def freeze(self):
        snap=self.snapshot();p=self.state/'frozen.json'
        if p.exists():need(read(p)==snap,'冻结来源已变化；请新建修订批次，不覆盖历史来源')
        else:write(p,snap)
        return {'ok':True,'source_files':len(snap),'frozen':True}

    def body(self,key,name):
        p=child(self.root,f'drafts/{key}/{name}.md');need(p.is_file(),'缺正文：'+str(p))
        text=p.read_text(encoding='utf-8-sig');need(nonempty(text),'正文为空：'+str(p));return text

    def build(self):
        need((self.state/'frozen.json').exists(),'先执行freeze')
        need(read(self.state/'frozen.json')==self.snapshot(),'来源/题干已变化，禁止沿用旧冻结数据')
        files={};problems=[];bodies={};paths={};edges={k:[] for k in self.items}
        for key,item in self.items.items():paths[key]=KINDS[item['kind']]+'/'+key+'.md'
        for key,item in self.items.items():
            for rel in item.get('related',[]):
                target=rel.get('id');need(target!=key and (target in self.items or target in self.catalog['cards']),'关系目标不存在：'+str(target))
                need(nonempty(rel.get('reason')),'关系缺少用途说明：'+key)
                edges[key].append((target,rel['reason']))
                if target in edges and (key,rel['reason']) not in edges[target]:edges[target].append((key,rel['reason']))
        source_outputs={}
        for key,s in self.sources.items():
            p=self.source_path(s);raw=p.read_bytes();ext=p.suffix.lower()
            need(re.fullmatch(r'\.[a-zA-Z0-9]{1,10}',ext),'来源扩展名不支持')
            filename='原始资料/'+key+'-'+sha(raw)[:16]+ext;files[filename]=raw;source_outputs[key]=filename
        for key,item in self.items.items():
            parts={}
            if item['state']=='ready':
                names=['answer','method'] if item['kind']=='question' else ['body']
                for name in names:
                    text=self.body(key,name);parts[name]=text
                    problems.extend({'id':key,'field':name,'message':e} for e in check_fragments.inspect(text))
                    errors,_=check_markdown.inspect(text)
                    problems.extend({'id':key,'field':name,'message':e} for e in errors)
                    problems.extend({'id':key,'field':name,**w} for w in check_tex_hygiene.inspect(text))
            statement=child(self.root,item['statement']).read_text(encoding='utf-8-sig') if item.get('statement') else ''
            if item['state']=='ready' and statement:
                problems.extend({'id':key,'field':'statement','message':e} for e in check_fragments.inspect(statement))
                errors,_=check_markdown.inspect(statement)
                problems.extend({'id':key,'field':'statement','message':e} for e in errors)
                problems.extend({'id':key,'field':'statement',**w} for w in check_tex_hygiene.inspect(statement))
            bodies[key]={'parts':parts,'statement':statement}
            pending=item['state']=='pending'
            title=item['title'] if not pending else '待核材料：'+key
            if not pending and item['kind']=='question' and item['provenance']=='authored' and '自编' not in title:title+='（自编）'
            text='# '+title+'\n\n'
            if pending:text+='> [!warning] 待核\n'+ '\n'.join('> '+line for line in item['reason'].splitlines())+'\n\n'
            elif item['kind']=='question':
                text+='## 题目\n\n'+statement+'\n\n> [!example]- 标准解答\n'
                text+='\n'.join('> '+line for line in parts['answer'].split('\n'))+'\n\n## 方法与易错点\n\n'+parts['method']+'\n\n'
            else:text+=parts['body']+'\n\n'
            # 来源归档与卡片展示分别控制；仅嵌入人工选定的必要局部图。
            display=item.get('display_source_ids',[x for x in item['source_ids'] if pending and self.sources[x]['kind']=='image'])
            for source_id in display:
                text+='![](../'+source_outputs[source_id]+')\n\n'
            if not pending and edges[key]:
                text+='\n## 关联内容\n\n'
                for target,reason in dict.fromkeys(edges[key]):
                    if target in self.items:
                        if self.items[target]['state']=='pending':continue
                        t=self.items[target];p=paths[target]
                    else:
                        t=self.catalog['cards'][target];p=t['path']
                        old=child(self.output,p);need(old.is_file() and file_sha(old)==self.catalog['files'].get(p),'既有引用已变更，须核对：'+target)
                    text+='- ['+t['title'].replace('[','').replace(']','')+'](../'+p+')：'+reason+'\n'
            files[paths[key]]=text.encode('utf-8')
        order=self.plan.get('learning_order',[k for k,i in self.items.items() if i['kind']=='topic'])
        need(len(order)==len(set(order)) and set(order)=={k for k,i in self.items.items() if i['kind']=='topic'},'learning_order须完整且只列本批知识点id')
        text='# '+self.config.get('title',self.config['batch_id'])+'\n\n## 学习顺序\n\n'
        for i,key in enumerate(order,1):text+=f'{i}. [{self.items[key]["title"] if self.items[key]["state"]=="ready" else "待核知识点"}](../{paths[key]})\n'
        text+='\n## 题目与技巧\n\n'
        for key,item in self.items.items():
            if item['kind']!='topic':text+=f'- [{item["title"] if item["state"]=="ready" else "待核材料"}](../{paths[key]})\n'
        files['章节/'+self.config['batch_id']+'.md']=text.encode('utf-8')
        # 已有引用的内容也参与版本，防止复核后被别的批次改变。
        external={target:self.catalog['files'][self.catalog['cards'][target]['path']] for pairs in edges.values() for target,_ in pairs if target not in self.items}
        revision=sha(json.dumps({'source':self.snapshot(),'bodies':bodies,'external':external,'version':VERSION,'engine':file_sha(Path(__file__))},sort_keys=True,ensure_ascii=False).encode('utf-8'))
        stage=self.state/'build'/revision
        manifest={name:sha(raw) for name,raw in files.items()}
        # 先核验已有文件，再补齐缺失文件；允许构建中断重跑，不覆盖被修改的成品。
        need(all(not child(stage,n).exists() or (child(stage,n).is_file() and file_sha(child(stage,n))==h) for n,h in manifest.items()),'已有构建目录内容被修改；请核对，禁止覆盖')
        for name,raw in files.items():
            if not child(stage,name).exists():write(child(stage,name),raw)
        report={'version':VERSION,'revision':revision,'stage':str(stage),'files':manifest,'issues':problems,'cards':{k:{'path':paths[k],'title':i['title'],'kind':i['kind'],'state':i['state']} for k,i in self.items.items()},'external':external}
        write(self.state/'build.json',report)
        return report

    def check(self):
        report=self.build();errors=list(report['issues']);p=self.root/'review.json'
        if not p.exists():errors.append({'message':'尚无review.json：草稿不能发布'})
        else:
            review=read(p)
            if review.get('revision')!=report['revision']:errors.append({'message':'复核对应旧版本，请核对变更后重做受影响项复核'})
            rows=review.get('items',[]);indexed={r.get('id'):r for r in rows}
            if len(indexed)!=len(rows) or set(indexed)!=set(self.items):errors.append({'message':'复核必须覆盖完整计划，不漏知识点/技巧'})
            for key,item in self.items.items():
                r=indexed.get(key,{})
                if item['state']=='pending':
                    if r.get('decision')!='pending' or not nonempty(r.get('next_action')):errors.append({'id':key,'message':'待核项缺后续补证动作'})
                else:
                    if r.get('decision')!='approved' or r.get('semantic_check')!='passed':errors.append({'id':key,'message':'专业复核尚未通过'})
                    expected='not_applicable' if item['provenance']=='authored' and not item['source_ids'] else 'matched'
                    if r.get('source_check')!=expected:errors.append({'id':key,'message':'来源未核定'})
                    if self.config.get('require_independent',True) and r.get('mode')!='independent':errors.append({'id':key,'message':'本项目要求独立复核'})
                if not nonempty(r.get('reviewer')) or not nonempty(r.get('scope')):errors.append({'id':key,'message':'缺审查者或范围'})
                evidence=r.get('evidence',[])
                if not isinstance(evidence,list) or not evidence:errors.append({'id':key,'message':'缺复核证据文件'})
                else:
                    for name in evidence:
                        e=child(self.root,name)
                        if not e.is_file() or not e.stat().st_size:errors.append({'id':key,'message':'证据文件缺失：'+name})
            visual=review.get('presentation',{})
            if visual.get('status')!='passed' or not nonempty(visual.get('method')) or not nonempty(visual.get('scope')):errors.append({'message':'需记录实际排版验收方式及范围'})
            if not visual.get('evidence'):errors.append({'message':'缺排版验收证据文件'})
            for name in visual.get('evidence',[]):
                e=child(self.root,name)
                if not e.is_file() or not e.stat().st_size:errors.append({'message':'排版证据文件缺失：'+name})
        out={'ok':not errors,'revision':report['revision'],'errors':errors,'scope':'文件版本、机械检查与复核记录；不能证明模型或人真的正确复核'}
        write(self.state/'check.json',out);return out

    def publish(self):
        with mutex(self.output/'.kb'):
            # 加锁后重新读目录，另一批次可能刚发布完。
            self.catalog=read(self.output/'.kb/catalog.json') if (self.output/'.kb/catalog.json').exists() else {'cards':{},'files':{}}
            checked=self.check();need(checked['ok'],'发布被拦截：'+json.dumps(checked['errors'],ensure_ascii=False))
            build=read(self.state/'build.json');stage=Path(build['stage']);review=read(self.root/'review.json')
            records={'revision':build['revision'],'review':review,'evidence_hashes':{name:file_sha(child(self.root,name)) for row in review['items'] for name in row['evidence']}}
            for name in review['presentation']['evidence']:records['evidence_hashes'][name]=file_sha(child(self.root,name))
            receipt='整理记录/'+self.config['batch_id']+'/'+build['revision'][:16]+'.json'
            files=dict(build['files']);records['archived_evidence']={}
            for name,h in records['evidence_hashes'].items():
                ext=Path(name).suffix or '.txt';rel='整理记录/证据/'+h+ext
                write(child(stage,rel),child(self.root,name).read_bytes());files[rel]=h;records['archived_evidence'][name]=rel
            write(child(stage,receipt),records);files[receipt]=file_sha(child(stage,receipt))
            for name,new in files.items():
                target=child(self.output,name)
                if target.exists():need(target.is_file() and file_sha(target) in [new,self.catalog['files'].get(name)],'目标存在未登记或手工修改内容，未覆盖：'+name)
            for key,row in build['cards'].items():
                old=self.catalog['cards'].get(key)
                need(not old or old['path']==row['path'],'已存在id不能更换条目类型：'+key)
            journal_path=self.output/'.kb/publish-journal.json'
            if journal_path.exists():
                previous=read(journal_path)
                need(not previous.get('remaining') or (previous.get('batch')==self.config['batch_id'] and previous.get('revision')==build['revision']),'存在未完成发布，请先用原批次/版本继续publish，避免混合发布')
            journal={'batch':self.config['batch_id'],'revision':build['revision'],'remaining':list(files)};write(journal_path,journal)
            changed=0
            for name,new in files.items():
                target=child(self.output,name);src=child(stage,name)
                need(file_sha(src)==new,'暂存成品已变化：'+name)
                if target.exists() and file_sha(target)==new:pass
                else:
                    if target.exists():
                        old=file_sha(target);need(old==self.catalog['files'].get(name),'复制前目标被修改：'+name)
                        backup=child(self.output,'.kb/history/'+old+'/'+name)
                        if not backup.exists():write(backup,target.read_bytes())
                    write(target,src.read_bytes());changed+=1
                need(file_sha(target)==new,'发布读回失败：'+name)
                journal['remaining'].remove(name);write(journal_path,journal)
            self.catalog['files'].update(files);self.catalog['cards'].update(build['cards']);write(self.output/'.kb/catalog.json',self.catalog)
            write(self.state/'published.json',{'revision':build['revision'],'files':files,'output':str(self.output)})
            return {'ok':True,'revision':build['revision'],'changed_files':changed,'files':len(files),'pending':sum(i['state']=='pending' for i in self.items.values()),'output':str(self.output)}

def init(root,output,batch,title):
    root=Path(root).resolve();need(not root.exists() or not any(root.iterdir()),'初始化目录必须为空')
    root.mkdir(parents=True,exist_ok=True);safe_id(batch)
    write(root/'project.json',{'version':1,'batch_id':batch,'title':title or batch,'output_dir':str(Path(output).resolve()),'require_independent':True})
    write(root/'plan.json',{'sources':[],'items':[],'learning_order':[]})
    (root/'drafts').mkdir();(root/'evidence').mkdir()
    return {'ok':True,'project':str(root),'next':'填plan与题干→freeze→正文→build→review.json→check→publish；status可随时恢复'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','freeze','build','check','publish','status']);p.add_argument('project',type=Path);p.add_argument('--output');p.add_argument('--batch',default='chapter-01');p.add_argument('--title');a=p.parse_args()
    try:
        if a.command=='init':need(a.output,'init需要--output');result=init(a.project,a.output,a.batch,a.title)
        elif a.command=='status':
            s=a.project/'.kb';result={'ok':True,'frozen':(s/'frozen.json').exists(),'last_build':read(s/'build.json').get('revision') if (s/'build.json').exists() else None,'last_check':read(s/'check.json') if (s/'check.json').exists() else None,'last_publication':read(s/'published.json') if (s/'published.json').exists() else None,'note':'这是保存的进度；继续时check/publish会重新核对当前内容，不把历史通过当当前通过'}
        else:result=getattr(Project(a.project),a.command)()
        if a.command=='build':result={k:v for k,v in result.items() if k not in ['files','cards','external']}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('ok',not result.get('issues')) else 1
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as e:print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False));return 1

if __name__=='__main__':sys.exit(main())
