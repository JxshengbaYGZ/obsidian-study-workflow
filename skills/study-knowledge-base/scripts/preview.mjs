// 可选独立网页验收；依赖由调用者提供，不捆绑个人目录，也不冒称Obsidian原生验收。
import fs from 'node:fs';import path from 'node:path';import {createRequire} from 'node:module';import {pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url),args=process.argv.slice(2),root=path.resolve(args.shift()||'.');
const options={};while(args.length){const k=args.shift();options[k]=args.shift();}
if(!options['--output'])throw new Error('需要 --output 预览证据目录');
const out=path.resolve(options['--output']);fs.mkdirSync(out,{recursive:true});
async function load(name,override){return import(pathToFileURL(require.resolve(override||name)).href);}
const km=await load('katex',options['--katex-module']),katex=km.default||km;
const mm=await load('marked',options['--marked-module']),marked=mm.marked||mm.default||mm;
const pw=await load('playwright',options['--playwright-module']);const chromium=pw.chromium||pw.default.chromium;
const css=options['--katex-css']||require.resolve('katex/dist/katex.min.css');
let count=0;const errors=[];const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
function parse(md,file){
 const codes=[];md=md.replace(/```[\s\S]*?```|`[^`\n]*`/g,s=>{codes.push(s);return `CODEMARKER${codes.length-1}END`;});
 const math=[];md=md.replace(/\$\$([\s\S]*?)\$\$|(?<!\\)\$(?!\$)([^\n$]+?)(?<!\\)\$/g,(all,block,inline)=>{const key=`MATHMARKER${math.length}END`;try{math.push(katex.renderToString(block??inline,{displayMode:block!==undefined,throwOnError:true}));count++;}catch(e){errors.push({file,error:e.message});math.push(escape(all));}return key;});
 codes.forEach((s,i)=>md=md.replaceAll(`CODEMARKER${i}END`,s));let html=marked.parse(md);math.forEach((s,i)=>html=html.replaceAll(`MATHMARKER${i}END`,s));
 return html.replace(/(src|href)="([^"#]+)"/g,(all,k,v)=>/^[a-z]+:/i.test(v)?all:`${k}="${pathToFileURL(path.resolve(path.dirname(file),decodeURIComponent(v))).href}"`);
}
const cards=[];
for(const folder of ['笔记','题','技巧','章节']){
 if(!fs.existsSync(path.join(root,folder)))continue;
 for(const name of fs.readdirSync(path.join(root,folder)).filter(x=>x.endsWith('.md'))){
  const file=path.join(root,folder,name),md=fs.readFileSync(file,'utf8');const match=md.match(/^> \[!(example|warning)\](-?)[^\n]*\n(?:>[^\n]*(?:\n|$))*/m);let html;
  if(match){const body=match[0].split('\n').slice(1).map(l=>l.replace(/^> ?/,'')).join('\n');const block=match[1]==='example'?`<details><summary>标准解答</summary>${parse(body,file)}</details>`:`<aside>${parse(body,file)}</aside>`;html=parse(md.slice(0,match.index),file)+block+parse(md.slice(match.index+match[0].length),file);}else html=parse(md,file);
  cards.push(`<article data-name="${escape(folder+'-'+name)}">${html}</article>`);
 }
}
fs.writeFileSync(path.join(out,'preview.html'),`<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="${pathToFileURL(path.resolve(css)).href}"><style>body{margin:0;background:#f6f4ef;font:16px/1.75 system-ui;color:#242424}main{max-width:820px;margin:auto;padding:16px}article{background:white;padding:18px;margin-bottom:24px;border-radius:8px}h1{font-size:24px}h2{font-size:19px}img{max-width:100%;height:auto}details,aside{border-left:3px solid #367582;background:#f1f8fa;padding:12px}summary{cursor:pointer;font-weight:600}.katex-display{overflow-x:auto;overflow-y:hidden;padding:8px 0}p{overflow-wrap:break-word}table{border-collapse:collapse;display:block;max-width:100%;overflow-x:auto;margin:16px 0}th,td{border:1px solid #b9cbcf;padding:6px 10px;text-align:center;white-space:nowrap}th{background:#e2eef0}</style><main><p>独立Markdown/KaTeX预览，不等同Obsidian原生界面。</p>${cards.join('')}</main>`);
const report={cards:cards.length,formulas:count,errors,views:[],scope:'独立网页实际题卡预览'};
const launch={headless:true};if(options['--channel'])launch.channel=options['--channel'];if(options['--browser-executable'])launch.executablePath=options['--browser-executable'];
let browser;try{browser=await chromium.launch(launch);const page=await browser.newPage();for(const width of [420,960]){await page.setViewportSize({width,height:1100});await page.goto(pathToFileURL(path.join(out,'preview.html')).href);await page.evaluate(()=>document.fonts.ready);await page.locator('details').evaluateAll(es=>es.forEach(e=>e.open=true));report.views.push({width,...await page.evaluate(()=>({body_overflow:document.documentElement.scrollWidth>innerWidth+2,broken_images:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length}))});await page.screenshot({path:path.join(out,`overview-${width}.png`)});if(width===960)for(const [i,article] of (await page.locator('article').all()).entries())await article.screenshot({path:path.join(out,`card-${i+1}.png`)});}}catch(e){report.errors.push({error:e.message});}finally{if(browser)await browser.close();}
fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));process.exitCode=report.errors.length||report.views.some(v=>v.body_overflow||v.broken_images)?1:0;
