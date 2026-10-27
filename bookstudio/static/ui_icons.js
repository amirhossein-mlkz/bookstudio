/* Book Studio v5.11 — lightweight self-contained icons. No CDN or font files.
 * Icons are decorative (aria-hidden) and labels remain accessible/plain text.
 * This module never modifies application data-key, ids, input values or events.
 */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const strokes = {
    book: '<path d="M4 5.5C7 4 9.5 4 12 6v14c-2.5-2-5-2-8-.5zM20 5.5C17 4 14.5 4 12 6v14c2.5-2 5-2 8-.5z"/>',
    chapters: '<rect x="4" y="4" width="5" height="16" rx="1"/><path d="M12 6h8M12 12h8M12 18h8"/>',
    file: '<path d="M6 3h8l5 5v13H6zM14 3v5h5M9 13h6M9 17h7"/>',
    folder: '<path d="M3 6h7l2 2h9v11H3z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    save: '<path d="M4 4h14l3 3v14H4zM8 4v6h9V4M8 21v-8h9v8"/>',
    download: '<path d="M12 3v12m-4-4 4 4 4-4M4 18v3h16v-3"/>',
    preview: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    settings: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="16" cy="12" r="2" fill="currentColor" stroke="none"/><circle cx="10" cy="18" r="2" fill="currentColor" stroke="none"/>',
    type: '<path d="M4 6V4h16v2M12 4v16M8 20h8"/>',
    colors: '<circle cx="12" cy="12" r="9"/><path d="M12 3v6M5 17l6-5M20 13h-5"/><circle cx="8" cy="8" r="1"/><circle cx="17" cy="17" r="1"/>',
    ruler: '<rect x="3" y="8" width="18" height="8" rx="1"/><path d="M7 8v4M11 8v3M15 8v4M19 8v3"/>',
    align: '<path d="M4 5h16M7 9h10M4 13h16M7 17h10M4 21h16"/>',
    move: '<path d="M12 2v20M2 12h20M9 5l3-3 3 3M9 19l3 3 3-3M5 9l-3 3 3 3m14-6 3 3-3 3"/>',
    layout: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M10 9v12"/>',
    list: '<path d="M9 5h12M9 12h12M9 19h12"/><path d="M4 5h1M4 12h1M4 19h1"/>',
    number: '<path d="M5 3 3 21M12 3l-2 18M2 9h17M1 15h17"/>',
    quote: '<path d="M10 5H6c-2 0-3 2-3 5v3h5v5l-5 3M21 5h-4c-2 0-3 2-3 5v3h5v5l-5 3"/>',
    footnote: '<path d="M3 5h18M4 10h12M4 14h10M4 19h7"/><path d="M16 17h5m-2.5-2.5v5"/>',
    image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="9" r="2"/><path d="m4 18 6-5 4 3 3-3 4 4"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v5M17 3v5M3 10h18"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-3c0-5 16-5 16 0v3"/>',
    check: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="m7 12 3 3 7-7"/>',
    arrow: '<path d="M12 4v16M7 15l5 5 5-5"/>',
    triangle: '<path d="m12 4 9 16H3z"/>',
    pen: '<path d="m4 16 11-11 4 4L8 20H4zM13 7l4 4"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 4 3c-1 1-1 1-1 3M12 18h.01"/>',
    trash: '<path d="M4 7h16M8 7V4h8v3M6 7l1 14h10l1-14M10 11v6M14 11v6"/>',
    back: '<path d="M15 18l-6-6 6-6"/>',
    next: '<path d="M9 18l6-6-6-6"/>',
    table: '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M3 9h18M3 15h18M10 3v18"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
    bookopen: '<path d="M3 4h6l3 2 3-2h6v15h-6l-3 2-3-2H3zM12 6v15"/>',
    margin: '<rect x="3" y="3" width="18" height="18"/><rect x="7" y="7" width="10" height="10" stroke-dasharray="2 2"/>',
  };
  const explicit = {
    newProjectBtn:'plus', openProjectBtn:'folder', openFolderBtn:'folder',
    saveBtn:'save',saveAsBtn:'save',renderBtn:'preview',pdfBtn:'download',promptBtn:'help',
    breakBtn:'layout',chapterBtn:'book',blankDecorBtn:'layout',openImageDialog:'image',
    footnoteBtn:'footnote',quoteBtn:'quote',
    sectionsTab:'chapters',frontTab:'bookopen',settingsTab:'settings',
    addChapterBtn:'plus',addPrefaceBtn:'plus',addIntroBtn:'plus',importManyBtn:'file',
    removeSectionBtn:'trash',sectionPdfBtn:'download',prevBtn:'back',nextBtn:'next',
    imageSubmit:'plus',imageCancel:'back',imageCloseSecondary:'back',closePrompt:'back',copyPrompt:'file',
    sectionTitle:'type',sectionRole:'chapters',sectionOdd1:'type',sectionOdd2:'type',
    sectionEven1:'type',sectionEven2:'type',sectionTitlePage:'layout',
    sectionHeadingEnabled:'check',sectionHeadingLabel:'type',sectionOpenerLabel:'type',sectionOpenerTitle:'type'
  };
  function resolve(node){
    if (node.id && explicit[node.id]) return explicit[node.id];
    const control=node.matches('label')?node.querySelector('input, select, textarea'):null;
    const key=control?.dataset?.key || control?.dataset?.frontKey || '';
    const text=(node.textContent||'').trim();
    if(/(color|background|_bg)$/.test(key) || /رنگ|زمینه|پس.زمینه/.test(text))return 'colors';
    if(/(padding|_pad_)/.test(key) || /پدینگ|حاشیه|فاصله/.test(text))return 'margin';
    if(/(height|width|size|margin|offset|line_height)/.test(key) || /عرض|ارتفاع|اندازه|میلی.متر|فاصله/.test(text))return 'ruler';
    if(/align|position/.test(key) || /تراز|موقعیت|جهت/.test(text))return 'align';
    if(/_(?:enabled|include_|show_)/.test(key) || /نمایش|فعال|غیرفعال/.test(text) || control?.type==='checkbox')return 'check';
    if(/year|date/.test(key) || /سال|تاریخ|نوبت چاپ/.test(text))return 'calendar';
    if(/author|publisher/.test(key) || /نویسنده|ناشر/.test(text))return 'user';
    if(/_(?:font|weight|text|title)/.test(key) || /فونت|متن|تیتر|عنوان|نوشته|مستطیل/.test(text))return 'type';
    if(/شماره|عدد|شمارگان|شروع/.test(text))return 'number';
    if(/فهرست|سطح|لیست/.test(text))return 'list';
    if(/پاورقی|فوتر/.test(text))return 'footnote';
    if(/نقل.قول|کوتیشن/.test(text))return 'quote';
    if(/شکل|تصویر/.test(text))return 'image';
    if(/فصل|بخش/.test(text))return 'chapters';
    if(/تقدیم|شناسنامه|صفحات اولیه/.test(text))return 'bookopen';
    if(/ویرایش|ویرایشگر|Markdown|MD/.test(text))return 'pen';
    if(/تنظیم|پیشرفته/.test(text))return 'settings';
    if(/ذخیره/.test(text))return 'save';
    if(/دانلود|PDF/.test(text))return 'download';
    if(/جدول/.test(text))return 'table';
    if(node.matches('summary'))return 'settings';
    if(node.matches('h2,h3,h4'))return 'book';
    if(node.matches('button,a'))return 'file';
    return 'settings';
  }
  function icon(name){
    const svg=document.createElementNS(NS,'svg');
    svg.setAttribute('class','bs-ui-icon');svg.setAttribute('viewBox','0 0 24 24');
    svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');
    svg.setAttribute('stroke-width','1.8');svg.setAttribute('stroke-linecap','round');
    svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');
    svg.innerHTML=strokes[name]||strokes.settings;
    return svg;
  }
  function apply(scope=document){
    const targets=scope.querySelectorAll(
      '.toolbar-actions button,.toolbar-actions a,.insert-menu-trigger,.insert-menu-panel button,'+
      '.project-nav h2,.project-nav h3,.project-nav h4,.project-nav label,.project-nav summary,'+
      '.project-nav .project-tab,.project-nav .project-add button,.project-nav .project-add a,'+
      '.editor .section-head h2,.editor .importlabel,'+
      '.preview .section-head h2,.preview .pager button,'+
      '.image-dialog h2,.image-dialog label,.image-dialog button,'+
      '.prompt-dialog h2,.prompt-dialog button'
    );
    for(const el of targets){
      if(el.classList.contains('bs-iconized') || el.querySelector(':scope > svg'))continue;
      el.insertBefore(icon(resolve(el)),el.firstChild);
      el.classList.add('bs-iconized');
    }
  }
  function init(){
    apply();
    // The selected Markdown section heading is set via textContent by app.js.
    const heading=document.getElementById('editingSectionName');
    if(heading)new MutationObserver(()=>{
      if(!heading.querySelector(':scope > svg')){
        heading.insertBefore(icon('pen'),heading.firstChild);
      }
    }).observe(heading,{childList:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
