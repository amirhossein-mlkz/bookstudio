const $ = id => document.getElementById(id);
let pages=0,page=1,dirty=false,revision=null,chapterStyles={},headingStyles={};
let sections=[], frontmatter={}, selectedSectionId=null, renderReady=false, editGeneration=0;

let cursor={start:0,end:0,scroll:0};
const fa=n=>String(n).replace(/\d/g,c=>'۰۱۲۳۴۵۶۷۸۹'[+c]);
function status(message){$('status').textContent=message}
function settings(){const r={chapter_styles:chapterStyles,heading_styles:headingStyles};document.querySelectorAll('[data-key]').forEach(el=>r[el.dataset.key]=el.type==='number'?Number(el.value):el.value);return r}
async function api(url,opt={}){const r=await fetch(url,opt);let obj;try{obj=await r.json()}catch{throw Error('پاسخ سرور معتبر نیست')}if(!r.ok)throw Error(obj.error||'خطای ناشناخته');return obj}
const jpost=(url,data)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
function change(){editGeneration++;dirty=true;renderReady=false;updatePdfDownloadLink();updateSectionExportLink();status('تغییرات جدید دارید؛ برای PDF جدید، پیش‌نمایش را دوباره بسازید.')}
function escapeHTML(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function syntax(line){let raw=escapeHTML(line);if(/^\s*<!-- CHAPTER -->/.test(line))return `<span class="md-chapter">${raw}</span>`;if(/^\s*<!-- PAGEBREAK -->/.test(line))return `<span class="md-break">${raw}</span>`;if(/^\s*<!-- BLANKPAGE -->/.test(line))return `<span class="md-break">${raw}</span>`;if(/^#{1,6}\s/.test(line))return `<span class="md-heading">${raw}</span>`;if(/!\[[^\]]*\]\(/.test(line))return `<span class="md-image">${raw}</span>`;if(/^\s*\|/.test(line)||/^جدول\s*:/.test(line))return `<span class="md-table">${raw}</span>`;return raw}
function highlight(){syncChapters();syncOutline()}
function syncScroll(){} // A single native textarea is the only painted text surface.
function syncOutline(){
  const text=$('markdown').value;
  const matches=[];
  const expr=/^(<!-- CHAPTER -->|#{1,3}\s+.+)$/gm;
  let match;
  while((match=expr.exec(text))!==null){
    const line=match[0];
    if(line==='<!-- CHAPTER -->')continue;
    const level=line.match(/^#+/)[0].length;
    matches.push({label:line.replace(/^#{1,3}\s+/,''),offset:match.index,type:level===1?'chapter':level===2?'heading2':'heading3'});
    if(matches.length>=150)break;
  }
  const sig=JSON.stringify(matches);
  if(sig===syncOutline.previous)return;
  syncOutline.previous=sig;
  const nav=$('mdOutline');
  nav.replaceChildren();
  if(!matches.length){const empty=document.createElement('span');empty.className='outline-empty';empty.textContent='هنوز فصلی یا تیتر داخلی وجود ندارد.';nav.append(empty);return;}
  for(const item of matches){
    const btn=document.createElement('button');btn.type='button';btn.className='outline-chip '+item.type;
    btn.textContent=item.label;btn.title='رفتن به: '+item.label;
    btn.addEventListener('click',()=>{
      const area=$('markdown');area.focus({preventScroll:true});area.setSelectionRange(item.offset,item.offset);
      const preceding=text.slice(0,item.offset).split('\n').length-1;
      const computed=getComputedStyle(area);const lineHeight=parseFloat(computed.lineHeight)||27;
      area.scrollTop=Math.max(0,preceding*lineHeight-area.clientHeight/3);
      remember();
    });nav.append(btn);
  }
}
function remember(){
  const a=$('markdown');
  cursor={start:a.selectionStart,end:a.selectionEnd,scroll:a.scrollTop};
}
function insertAtCursor(text, snapshot=cursor){
  const a=$('markdown');
  const start=Math.max(0,Math.min(snapshot.start,a.value.length));
  const end=Math.max(start,Math.min(snapshot.end,a.value.length));
  const top=snapshot.scroll;
  // Keep the native textarea as the sole text/caret surface. Avoid focus-driven
  // scrolling, including after the async image upload has completed.
  a.setRangeText(text,start,end,'end');
  a.scrollTop=top;
  highlight();change();
  a.focus({preventScroll:true});
  a.scrollTop=top;
  // Browsers may adjust textarea scroll after selection/focus in a later frame.
  requestAnimationFrame(()=>{a.scrollTop=top;remember()});
}
function chapterTitles(){return sections.filter(s=>s.role==='chapter').map(s=>s.title)}
let previousChapterList='';
function syncChapters(){const titles=chapterTitles(),signature=JSON.stringify(titles);if(signature===previousChapterList)return;previousChapterList=signature;const el=$('chapterSelect'),prior=el.value;el.replaceChildren();titles.forEach((t,i)=>{let opt=document.createElement('option');opt.value=String(i+1);opt.textContent=fa(i+1)+' — '+t;el.append(opt)});if(titles.length){el.value=titles.some((_,i)=>String(i+1)===prior)?prior:'1';loadChapterStyle()}else{const opt=document.createElement('option');opt.textContent='فصلی یافت نشد';el.append(opt)}}
function loadHeadingStyle(){const level=$('headingLevel').value;const fallback=level==='h1'?{background:'#1f2656',color:'#ffffff',triangle_color:'#7d81a4',font_size:13,font_weight:700}:level==='h2'?{background:'#575A84',color:'#ffffff',font_size:13,font_weight:700}:{background:'#D1D1E0',color:'#575A84',font_size:12,font_weight:700};const st=headingStyles[level]||fallback;$('headingBg').value=st.background;$('headingColor').value=st.color;$('headingSize').value=st.font_size;$('headingWeight').value=String(st.font_weight??700);$('headingTriangleWrap').hidden=level!=='h1';$('headingTriangleColor').value=st.triangle_color||'#7d81a4'}
function updateHeadingStyle(){const level=$('headingLevel').value;const current=headingStyles[level]||{};headingStyles[level]={...current,background:$('headingBg').value,color:$('headingColor').value,font_size:Number($('headingSize').value),font_weight:Number($('headingWeight').value)};if(level==='h1')headingStyles[level].triangle_color=$('headingTriangleColor').value;change()}
function loadChapterStyle(){const c=chapterStyles['1']||{};$('chapterBg').value=c.background||settings().navy||'#202852';$('chapterSize').value=c.font_size??19;$('chapterWeight').value=String(c.font_weight==='normal'?400:c.font_weight==='bold'?700:(c.font_weight??700))}
function updateChapter(){const key='1';chapterStyles[key]={background:$('chapterBg').value,font_size:Number($('chapterSize').value),font_weight:Number($('chapterWeight').value)};change()}
let projectFolder=null;
function showProjectFolder(folder){projectFolder=folder||null;const label=$('projectFolderLabel');label.textContent=projectFolder?('پروژه: '+projectFolder):'پروژه هنوز در پوشه‌ای ذخیره نشده';label.title=projectFolder||'هنوز پروژه ذخیره نشده است';}
function currentSection(){return sections.find(s=>s.id===selectedSectionId)}
function syncCurrentSection(){const s=currentSection();if(s)s.markdown=$('markdown').value;}
function saveFrontFields(){document.querySelectorAll('[data-front-key]').forEach(el=>{frontmatter[el.dataset.frontKey]=el.type==='checkbox'?el.checked:el.type==='number'?Number(el.value):el.value})}
function fillFrontFields(){document.querySelectorAll('[data-front-key]').forEach(el=>{const v=frontmatter[el.dataset.frontKey];if(v===undefined)return;if(el.type==='checkbox')el.checked=!!v;else el.value=v})}
function sectionLabel(s,i){const role=s.role==='preface'?'پیشگفتار':s.role==='introduction'?'مقدمه':'فصل '+fa(sections.filter((p,j)=>j<=i&&p.role==='chapter').length);return `${role} — ${s.title}`;}
function populateSections(){
  const list=$('sectionList');list.replaceChildren();sections.forEach((s,i)=>{
    const row=document.createElement('button');row.type='button';row.className='section-item'+(s.id===selectedSectionId?' active':'');row.draggable=true;row.dataset.id=s.id;
    const handle=document.createElement('span');handle.className='drag-handle';handle.textContent='☷';const title=document.createElement('span');title.className='section-item-title';title.textContent=sectionLabel(s,i);
    row.append(handle,title);row.addEventListener('click',()=>selectSection(s.id));
    row.addEventListener('dragstart',e=>{e.dataTransfer.setData('text/plain',s.id);e.dataTransfer.effectAllowed='move';row.classList.add('dragging')});
    row.addEventListener('dragend',()=>row.classList.remove('dragging'));
    row.addEventListener('dragover',e=>{e.preventDefault();e.dataTransfer.dropEffect='move';row.classList.add('drag-over')});
    row.addEventListener('dragleave',()=>row.classList.remove('drag-over'));
    row.addEventListener('drop',e=>{e.preventDefault();row.classList.remove('drag-over');const id=e.dataTransfer.getData('text/plain');reorderSection(id,s.id)});
    list.append(row)
  });
}
function selectSection(id){
  syncCurrentSection();const s=sections.find(x=>x.id===id);if(!s)return;
  selectedSectionId=id;$('markdown').value=s.markdown;$('sectionTitle').value=s.title;$('sectionRole').value=s.role;
  $('sectionOdd1').value=s.odd_tab_text_1||'';$('sectionOdd2').value=s.odd_tab_text_2||'';
  $('sectionEven1').value=s.even_tab_text_1||'';$('sectionEven2').value=s.even_tab_text_2||'';
  $('sectionTitlePage').checked=s.include_title_page!==false;
  $('sectionHeadingEnabled').checked=s.include_heading_label!==false;
  $('sectionHeadingLabel').value=s.heading_label_text||'';
  $('sectionHeadingLabel').disabled=s.include_heading_label===false;
  $('sectionOpenerLabel').value=s.opener_label_text||'';
  $('sectionOpenerTitle').value=s.opener_title_text||'';
  $('sectionHeadingLabel').placeholder='پیش‌فرض: '+s.title;
  $('sectionOpenerLabel').placeholder='پیش‌فرض: '+(s.role==='preface'?'پیشگفتار':s.role==='introduction'?'مقدمه':'فصل');
  $('sectionOpenerTitle').placeholder='پیش‌فرض: '+s.title;
  $('editingSectionName').textContent='متن: '+s.title;
  previousChapterList='';highlight();populateSections();remember();updateSectionExportLink();
}
function reorderSection(sourceId,targetId){
  if(!sourceId||sourceId===targetId)return;
  syncCurrentSection();const from=sections.findIndex(x=>x.id===sourceId);const to=sections.findIndex(x=>x.id===targetId);
  if(from<0||to<0)return;
  const draft=[...sections];draft.splice(to,0,draft.splice(from,1)[0]);
  const firstChapter=draft.findIndex(x=>x.role==='chapter');
  if(firstChapter>=0&&draft.some((x,i)=>i>firstChapter&&x.role!=='chapter')){status('پیشگفتار و مقدمه باید پیش از فصل‌ها قرار بگیرند.');return;}
  sections=draft;populateSections();change();renderReady=false;revision=null;updatePdfDownloadLink();updateSectionExportLink();
}
function sectionId(){return [...crypto.getRandomValues(new Uint8Array(6))].map(n=>n.toString(16).padStart(2,'0')).join('')}
function addSection(role='chapter'){
  if(role!=='chapter'&&sections.some(s=>s.role===role)){alert('این نوع بخش از قبل وجود دارد.');return;}
  syncCurrentSection();const title=role==='preface'?'پیشگفتار':role==='introduction'?'مقدمه':'فصل جدید';
  const s={id:sectionId(),title,role,markdown:`## ${title}\n\nمتن جدید را وارد کنید.\n`,odd_tab_text_1:'',odd_tab_text_2:'',even_tab_text_1:'',even_tab_text_2:'',include_title_page:true,include_heading_label:true};
  if(role==='preface')sections.unshift(s);else if(role==='introduction')sections.splice(sections[0]?.role==='preface'?1:0,0,s);else sections.push(s);
  selectSection(s.id);change();renderReady=false;
}
function removeSection(){if(sections.length<=1){alert('کتاب باید حداقل یک بخش داشته باشد.');return;}
  const s=currentSection();if(!s||!confirm('بخش «'+s.title+'» حذف شود؟'))return;
  const at=sections.indexOf(s);sections.splice(at,1);selectedSectionId=null;selectSection(sections[Math.max(0,at-1)].id);change();renderReady=false;
}
function updatePdfDownloadLink(){
  const a=$('pdfBtn'),ready=renderReady&&!dirty&&!!revision;
  a.href=ready?'/api/pdf?v='+encodeURIComponent(revision):'#';
  a.classList.toggle('disabled',!ready);a.setAttribute('aria-disabled',String(!ready));
  a.title=ready?'دانلود همان PDF استفاده‌شده در پیش‌نمایش':'ابتدا پیش‌نمایش تازه بسازید';
}
function updateSectionExportLink(){const s=currentSection(),a=$('sectionPdfBtn');if(!s)return;
  const ready=renderReady&&!dirty&&!!revision;
  a.href=ready?'/api/pdf/section/'+s.id+'?v='+encodeURIComponent(revision):'#';
  a.classList.toggle('disabled',!ready);a.setAttribute('aria-disabled',String(!ready));
}
function collectProject(){syncCurrentSection();saveFrontFields();return {sections,frontmatter,settings:settings()}}
async function storeWorkspace(){const d=await jpost('/api/project',collectProject());if(d.project_folder)showProjectFolder(d.project_folder);renderReady=false;revision=null;updatePdfDownloadLink();updateSectionExportLink();return d;}
async function save(){status('در حال ذخیره...');await storeWorkspace();if(!projectFolder){const d=await jpost('/api/project/save-as',{});if(d.cancelled){status('فضای کاری ذخیره شد، انتخاب پوشه لغو شد');return;}showProjectFolder(d.project_folder)}dirty=false;status('پروژه ذخیره شد');}
async function saveAs(){await storeWorkspace();const d=await jpost('/api/project/save-as',{});if(d.cancelled){status('انتخاب پوشه لغو شد');return;}showProjectFolder(d.project_folder);dirty=false;status('پروژه در پوشه جدید ذخیره شد');}
async function openProject(mode){if(dirty&&!confirm('تغییرات ذخیره‌نشده از دست بروند؟'))return;const d=await jpost('/api/project/open',{mode});if(d.cancelled)return;
  loadData(d);showProjectFolder(d.folder);resetPreview();status('پروژه باز شد');}
function resetPreview(){pages=0;page=1;revision=null;renderReady=false;$('thumbs').replaceChildren();$('pageImage').removeAttribute('src');$('empty').style.display='block';$('empty').textContent='برای مشاهده صفحات پیش‌نمایش را بسازید.';$('pageCount').textContent='—';$('pageTotal').textContent='/ ۰';$('pageNo').value=1;updatePdfDownloadLink();updateSectionExportLink()}
async function newProject(){if(dirty&&!confirm('پروژه جدید ساخته شود و تغییرات ذخیره‌نشده کنار گذاشته شوند؟'))return;
  const d=await jpost('/api/project/new',{});loadData(d);showProjectFolder(null);resetPreview();status('پروژه جدید آماده است');}
let shortcutBusy=false;
window.addEventListener('keydown',async event=>{
  if(!(event.ctrlKey||event.metaKey)||event.altKey||event.shiftKey)return;
  const key=event.key.toLowerCase();
  if(key!=='s'&&key!=='n')return;
  event.preventDefault();
  if(shortcutBusy)return;
  shortcutBusy=true;
  try{if(key==='s')await save();else await newProject()}
  catch(e){status(e.message);alert(e.message)}
  finally{shortcutBusy=false}
});
function showPage(p){if(p<1||p>pages)return;page=p;$('empty').style.display='none';$('pageImage').src=`/api/page/${p}.png?v=${revision}`;$('pageNo').value=p;[...$('thumbs').children].forEach((c,i)=>c.classList.toggle('active',i===p-1))}
function setPages(count){pages=count;$('pageCount').textContent=`${fa(count)} صفحه`;$('pageTotal').textContent=`/ ${fa(count)}`;$('pageNo').max=count;const thumbs=$('thumbs');thumbs.replaceChildren();for(let i=1;i<=Math.min(count,150);i++){let b=document.createElement('img');b.loading='lazy';b.alt='صفحه '+fa(i);b.src=`/api/page/${i}.png?v=${revision}`;b.onclick=()=>showPage(i);thumbs.append(b)}if(count)showPage(Math.min(page,count))}
async function render(){const b=$('renderBtn');b.disabled=true;const requestedGeneration=editGeneration;
  try{await storeWorkspace();status('در حال صفحه‌آرایی کل کتاب...');const res=await jpost('/api/render',{});
    revision=res.revision;setPages(res.pages);
    if(editGeneration!==requestedGeneration){
      dirty=true;renderReady=false;updatePdfDownloadLink();updateSectionExportLink();
      status('هنگام رندر تغییر جدیدی انجام شده است؛ پیش‌نمایش را دوباره بسازید.');
    }else{
      dirty=false;renderReady=true;updatePdfDownloadLink();updateSectionExportLink();
      status(`${fa(res.pages)} صفحه آماده شد؛ ${fa(res.toc_entries)} مدخل فهرست`);
    }
  }catch(e){status(e.message);alert(e.message)}finally{b.disabled=false}}
function loadData(data){
  sections=data.sections||[];frontmatter=data.frontmatter||{};chapterStyles=data.settings.chapter_styles||{};headingStyles=data.settings.heading_styles||{};
  document.querySelectorAll('[data-key]').forEach(el=>{if(data.settings[el.dataset.key]!==undefined)el.value=data.settings[el.dataset.key]});
  fillFrontFields();previousChapterList='';selectedSectionId=null;
  if(sections.length)selectSection(sections[0].id);loadHeadingStyle();loadChapterStyle();dirty=false;cursor={start:0,end:0,scroll:0};renderReady=false;revision=null;updatePdfDownloadLink();updateSectionExportLink();
}
$('markdown').addEventListener('click',remember);$('markdown').addEventListener('keyup',remember);$('markdown').addEventListener('select',remember);$('markdown').addEventListener('scroll',()=>{remember();syncScroll()});$('markdown').addEventListener('input',()=>{remember();syncCurrentSection();highlight();change();renderReady=false;updateSectionExportLink()});
// Remember the insertion point before toolbar focus moves away from the editor.
// Opening the top menu steals focus from the textarea: snapshot selection first.
$('insertMenu').querySelector('summary').addEventListener('pointerdown',()=>{
  if(document.activeElement===$('markdown'))remember();
},{capture:true});
['breakBtn','chapterBtn','blankDecorBtn','openImageDialog','footnoteBtn','quoteBtn'].forEach(id=>$(id).addEventListener('pointerdown',()=>{
  if(document.activeElement===$('markdown'))remember();
},{capture:true}));
function closeInsertMenu(){ $('insertMenu').open=false; }
// Close when clicking outside the menu, or pressing Escape.
document.addEventListener('pointerdown',event=>{
  if(!$('insertMenu').contains(event.target))closeInsertMenu();
});
document.addEventListener('keydown',event=>{
  if(event.key==='Escape' && $('insertMenu').open){closeInsertMenu();$('insertMenu').querySelector('summary').focus();}
});
$('breakBtn').onclick=()=>{closeInsertMenu();insertAtCursor('\n\n<!-- PAGEBREAK -->\n\n');};
$('chapterBtn').onclick=()=>{closeInsertMenu();insertAtCursor('\n\n<!-- CHAPTER -->\n\n# عنوان فصل\n\n');};
$('blankDecorBtn').onclick=()=>{closeInsertMenu();insertAtCursor('\n\n<!-- BLANKPAGE -->\n\n');};
$('quoteBtn').onclick=()=>{
  closeInsertMenu();
  const selected=$('markdown').value.slice(cursor.start,cursor.end).trim();
  const content=selected || 'متن نقل‌قول را اینجا بنویسید.';
  insertAtCursor('\n\n:::quote position='+document.querySelector('[data-key=\"quote_position\"]')?.value+'\n'+content+'\n-- توضیح کوتاه در حاشیه\n:::\n\n');
};
$('footnoteBtn').onclick=()=>{
  closeInsertMenu();
  const area=$('markdown');
  const used=new Set([...area.value.matchAll(/\[\^([^\]]+)\]/g)].map(m=>m[1]));
  let number=1; while(used.has(String(number)))number++;
  const anchor='[^'+number+']';
  const snapshot={...cursor};
  const selected=area.value.slice(snapshot.start,snapshot.end);
  insertAtCursor(selected+anchor, snapshot);
  const finalText='\n\n'+anchor+': متن پاورقی را اینجا بنویسید.\n';
  area.setRangeText(finalText,area.value.length,area.value.length,'preserve');
  highlight();change();
  status('پاورقی '+fa(number)+' درج شد؛ توضیح آن به انتهای Markdown افزوده شد.');
};
let imageInsertion=null;
$('openImageDialog').onclick=()=>{
  closeInsertMenu();
  imageInsertion={...cursor};
  $('imageFile').value='';
  $('imageCaption').value='';
  $('imageWidth').value='75';
  $('imageError').textContent='';
  $('imageSubmit').disabled=false;
  $('imageDialog').showModal();
};
$('imageCancel').onclick=()=>$('imageDialog').close();
$('imageDialog').addEventListener('close',()=>{imageInsertion=null});
$('imageFile').addEventListener('change',()=>{
  const f=$('imageFile').files[0];
  if(f && !$('imageCaption').value.trim())$('imageCaption').value=f.name.replace(/\.[^.]+$/,'').replace(/[-_]+/g,' ');
});
$('imageForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const file=$('imageFile').files[0];
  if(!file){$('imageError').textContent='یک تصویر انتخاب کنید.';return;}
  const width=Number($('imageWidth').value);
  if(!Number.isFinite(width)||width<5||width>100){$('imageError').textContent='عرض تصویر باید بین ۵ تا ۱۰۰ درصد باشد.';return;}
  const caption=$('imageCaption').value.trim().replace(/[\r\n]+/g,' ');
  const btn=$('imageSubmit');btn.disabled=true;$('imageError').textContent='در حال افزودن تصویر...';
  const insertion={...(imageInsertion||cursor)};
  try{
    const fd=new FormData();fd.append('file',file);
    const response=await api('/api/upload-image',{method:'POST',body:fd});
    // Keep the server-provided, sanitized relative image path; only customize alt text.
    const md=caption?response.markdown.replace(/^!\[[^\]]*\]/,'!['+caption.replace(/]/g,'\\]')+']'):response.markdown;
    $('imageDialog').close();
    insertAtCursor('\n\n'+md+'{width='+width+'%}\n\n',insertion);
    status('تصویر در محل نشانگر درج شد.');
  }catch(e){$('imageError').textContent=e.message;btn.disabled=false;}
});
$('mdFile').onchange=async function(){const f=this.files[0];if(!f)return;if(f.size>3*1024*1024){alert('فایل بزرگ است');return}if(!confirm('متن فعلی با فایل جدید جایگزین شود؟'))return;$('markdown').value=await f.text();syncCurrentSection();$('markdown').scrollTop=0;$('markdown').setSelectionRange(0,0);remember();highlight();change()};
$('newProjectBtn').onclick=async()=>{try{await newProject()}catch(e){status(e.message);alert(e.message)}};
$('saveBtn').onclick=async()=>{try{await save()}catch(e){status(e.message);alert(e.message)}};
$('saveAsBtn').onclick=async()=>{try{await saveAs()}catch(e){status(e.message);alert(e.message)}};
$('openProjectBtn').onclick=async()=>{try{await openProject('file')}catch(e){status(e.message);alert(e.message)}};
$('openFolderBtn').onclick=async()=>{try{await openProject('folder')}catch(e){status(e.message);alert(e.message)}};
$('headingLevel').addEventListener('change',loadHeadingStyle);['headingBg','headingColor','headingSize','headingWeight','headingTriangleColor'].forEach(id=>$(id).addEventListener('input',updateHeadingStyle));$('chapterSelect').addEventListener('change',loadChapterStyle);['chapterBg','chapterSize','chapterWeight'].forEach(id=>$(id).addEventListener('input',updateChapter));
$('renderBtn').onclick=render;$('nextBtn').onclick=()=>showPage(page+1);$('prevBtn').onclick=()=>showPage(page-1);$('pageNo').onchange=()=>showPage(Number($('pageNo').value));
const sidebarTabs=[['sectionsTab','sectionControls'],['frontTab','frontControls'],['settingsTab','templateControls']];
function switchSidebarTab(target){
  for(const [buttonId,panelId] of sidebarTabs){
    const active=buttonId===target;
    $(buttonId).classList.toggle('active',active);
    $(buttonId).setAttribute('aria-selected',String(active));
    $(buttonId).tabIndex=active?0:-1;
    $(panelId).hidden=!active;
  }
}
for(const [buttonId] of sidebarTabs){
  $(buttonId).addEventListener('click',()=>switchSidebarTab(buttonId));
  $(buttonId).addEventListener('keydown',event=>{
    if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
    event.preventDefault();
    let next=sidebarTabs.findIndex(([key])=>key===buttonId);
    if(event.key==='Home')next=0;
    else if(event.key==='End')next=sidebarTabs.length-1;
    else next=(next+(event.key==='ArrowLeft'?1:-1)+sidebarTabs.length)%sidebarTabs.length;
    switchSidebarTab(sidebarTabs[next][0]);$(sidebarTabs[next][0]).focus();
  });
}
$('addChapterBtn').onclick=()=>addSection('chapter');$('addPrefaceBtn').onclick=()=>addSection('preface');$('addIntroBtn').onclick=()=>addSection('introduction');$('removeSectionBtn').onclick=removeSection;
$('importManyBtn').onclick=()=>$('importManyFiles').click();
$('importManyFiles').onchange=async function(){
  const files=[...this.files];this.value='';if(!files.length)return;
  if(sections.length+files.length>160){alert('حداکثر ۱۶۰ بخش مجاز است.');return;}
  syncCurrentSection();let last=null;
  for(const file of files){if(file.size>3*1024*1024){alert('فایل '+file.name+' بیش از حد بزرگ است.');continue;}
    const content=await file.text();const header=content.match(/^#\s+(.+)$/m);
    const title=(header?.[1]||file.name.replace(/\.md$/i,'')).trim();
    last={id:sectionId(),title,role:'chapter',markdown:content,odd_tab_text_1:'',odd_tab_text_2:'',even_tab_text_1:'',even_tab_text_2:'',include_title_page:true,include_heading_label:true};sections.push(last);
  }
  if(last){selectSection(last.id);change();renderReady=false;status('فایل‌های Markdown به ترتیب انتخاب‌شده به پروژه اضافه شدند.');}
};
$('sectionTitle').addEventListener('input',()=>{const s=currentSection();if(!s)return;s.title=$('sectionTitle').value.trim()||'بدون عنوان';$('editingSectionName').textContent='متن: '+s.title;$('sectionHeadingLabel').placeholder='پیش‌فرض: '+s.title;$('sectionOpenerTitle').placeholder='پیش‌فرض: '+s.title;populateSections();change();renderReady=false;updateSectionExportLink()});
$('sectionRole').addEventListener('change',()=>{const s=currentSection();if(!s)return;const role=$('sectionRole').value;
  if(role!=='chapter'&&sections.some(p=>p!==s&&p.role===role)){alert('پیشگفتار یا مقدمه از قبل وجود دارد.');$('sectionRole').value=s.role;return;}
  s.role=role;$('sectionOpenerLabel').placeholder='پیش‌فرض: '+(role==='preface'?'پیشگفتار':role==='introduction'?'مقدمه':'فصل');sections=sections.filter(x=>x!==s);if(role==='preface')sections.unshift(s);else if(role==='introduction')sections.splice(sections[0]?.role==='preface'?1:0,0,s);else sections.push(s);populateSections();change();renderReady=false;});
$('sectionTitlePage').addEventListener('change',()=>{const s=currentSection();if(!s)return;s.include_title_page=$('sectionTitlePage').checked;change();renderReady=false;updateSectionExportLink()});
$('sectionHeadingEnabled').addEventListener('change',()=>{const s=currentSection();if(!s)return;s.include_heading_label=$('sectionHeadingEnabled').checked;$('sectionHeadingLabel').disabled=!s.include_heading_label;change();updateSectionExportLink()});
[['sectionOdd1','odd_tab_text_1'],['sectionOdd2','odd_tab_text_2'],
 ['sectionEven1','even_tab_text_1'],['sectionEven2','even_tab_text_2'],
 ['sectionHeadingLabel','heading_label_text'],['sectionOpenerLabel','opener_label_text'],
 ['sectionOpenerTitle','opener_title_text']].forEach(([id,key])=>$(id).addEventListener('input',()=>{const s=currentSection();if(s){s[key]=$(id).value;change();renderReady=false;updateSectionExportLink()}}));
document.querySelectorAll('[data-front-key]').forEach(el=>el.addEventListener('input',()=>{saveFrontFields();change();renderReady=false;updateSectionExportLink()}));
$('sectionPdfBtn').addEventListener('click',e=>{if(!renderReady||dirty)e.preventDefault()});
$('pdfBtn').addEventListener('click',e=>{if(!renderReady||dirty){e.preventDefault();status('ابتدا پیش‌نمایش تازه بسازید تا PDF مطابق آن دانلود شود.')}});
updatePdfDownloadLink();
document.querySelectorAll('[data-key]').forEach(el=>el.addEventListener('input',change));
api('/api/project').then(d=>{loadData(d);showProjectFolder(d.project_folder);status('پروژه بارگذاری شد');if(d.has_pdf)$('empty').textContent='برای بازبینی صفحات، پیش‌نمایش را بسازید'}).catch(e=>status(e.message));
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue=''}});

// Prompt is a local static asset; no network or external AI service is required.
$('promptBtn').addEventListener('click', async () => {
  try {
    if (!$('promptText').value) {
      const r = await fetch('/static/markdown_prompt.txt');
      if (!r.ok) throw new Error('فایل راهنما در دسترس نیست');
      $('promptText').value = await r.text();
    }
    $('promptDialog').showModal();
  } catch (e) { alert(e.message); }
});
$('closePrompt').addEventListener('click', () => $('promptDialog').close());
$('copyPrompt').addEventListener('click', async () => {
  const content = $('promptText').value;
  try {
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(content);
    else {
      $('promptText').focus(); $('promptText').select();
      if (!document.execCommand('copy')) throw new Error('لطفاً متن را دستی انتخاب و کپی کنید');
    }
    $('promptStatus').textContent = 'پرامپت کپی شد.';
  } catch(e) { $('promptStatus').textContent = e.message; }
});
