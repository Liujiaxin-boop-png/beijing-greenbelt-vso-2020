from pathlib import Path
import json,hashlib,re
P=Path(__file__).resolve().parent
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
source_call={'id':'ANPC2026_CALL','title':'2026中国城市规划年会征文启事（含学术论文撰稿须知）','publisher':'中国城市规划学会/中国城市规划网','url':'http://www.planning.cn/view.php?id=1095','page_date':'2026-01-04 09:08','signed_date':'2026-01-01','local_html':'official_call_1095.html','local_text':'official_call_1095.txt','access_note':'官方HTTP页面成功获取；HTTPS主机证书不匹配/网页工具自动HTTPS失败，不混作正文不存在。'}
source_result={'id':'ANPC2026_RESULTS','title':'2026中国城市规划年会论文评审结果线上查询通道开启','publisher':'中国城市规划学会/中国城市规划网','url':'http://www.planning.cn/view.php?id=1097','page_date':'2026-06-01 10:22','local_html':'official_review_results_1097.html','local_text':'official_review_results_1097.txt'}
source_reg={'id':'ANPC2026_REGISTRATION','title':'关于召开2026中国城市规划年会的通知','publisher':'中国城市规划学会/中国城市规划网','url':'http://www.planning.cn/view.php?id=1135','page_date':'2026-10-18 10:00','signed_date':'2026-10-18','document_number':'中规学字〔2026〕22号','local_html':'official_registration_1135.html','local_text':'official_registration_1135.txt','attachment_url':'https://www.planning.org.cn/uploads/ueditor/php/upload/file/20261019/1792375052155686.pdf'}
def rule(k,value,loc):return {'field':k,'value':value,'status':'VERIFIED_OFFICIAL2026_MAIN_CONFERENCE','source':'ANPC2026_CALL','locator':loc}
rules=[
 rule('length_max_excluding_references',8000,'撰稿须知2.3.1'),rule('columns',1,'2.3.1'),rule('page_size','A4','2.3.2'),rule('margins_mm',{'top':25.4,'bottom':25.4,'left':31.8,'right':31.8},'2.3.2'),
 rule('main_title_max_characters',20,'2.3.3'),rule('main_title_format',{'font':'宋体','size_cn':'三号','bold':True,'alignment':'center'},'2.3.3'),
 rule('abstract_words_characters',[300,500],'2.3.4'),rule('abstract_content',['研究目的','技术方法','创新点','主要结论'],'2.3.4'),rule('keywords_count',[3,7],'2.3.4'),rule('abstract_keywords_format',{'font':'楷体','size_cn':'小五号','alignment':'left','first_line_indent_characters':2,'space_before':'标题后空两行'},'2.3.4'),
 rule('body_format',{'font':'宋体','size_cn':'五号','alignment':'left','first_line_indent_characters':2,'line_spacing':1.5,'space_before':'摘要关键词后空两行'},'2.3.5'),
 rule('heading_numbering','1、1.1、1.1.1、1.1.1.1……','2.3.5'),rule('heading1',{'font':'黑体','size_cn':'四号','alignment':'left'},'2.3.5'),rule('heading2',{'font':'宋体','size_cn':'小四号','bold':True},'2.3.5'),rule('heading3',{'font':'楷体','size_cn':'小四号'},'2.3.5'),rule('heading4','同正文','2.3.5'),
 rule('notes_references',{'position':'正文后','heading_alignment':'center','font':'楷体','size_cn':'小五号','alignment':'left','first_line_indent_characters':2,'line_spacing':1.5},'2.3.6'),
 rule('anonymous_review',True,'征文启事三6、四1；撰稿须知3.2'),rule('author_identity_in_article','不得在文章、脚注、尾注中泄露作者个人信息；作者信息通过平台填写','撰稿须知3.2'),
 rule('funding_with_identifying_information','相关项目以脚注注明并标项目编号；涉及作者身份的完整版按须知于截稿前另发平台显示邮箱','撰稿须知1.7'),
 rule('map_requirement','通知要求论文地图遵守地图管理与审核要求，并提醒避免出现完整县级以上行政界线等须审核地图','撰稿须知3.1'),
 rule('no_simultaneous_similar_submission',True,'撰稿须知1.3'),rule('edit_after_deadline',False,'征文启事三5；撰稿须知3.3')]
unknown=[{'field':x,'status':'NOT_EXPLICIT_IN_VERIFIED_2026_NOTICE_DO_NOT_IMPORT_OTHER_VENUE_RULES'} for x in ['图表数量上限','图片DPI具体下限','图题表题字体字号','参考文献著录标准版本','英文题名/英文摘要是否必需','DOC或DOCX具体扩展名限制','查重率具体数值阈值','作者人数上限','附件图片是否须另打包','副标题单独字数限制']]
record={'status':'OFFICIAL_MAIN_CONFERENCE_RULES_VERIFIED_STANDARD_CALL_CLOSED','checked_date':'2026-11-06','target':'2026中国城市规划年会（主会）','organizer':'中国城市规划学会','theme':'城市规划70年：经纬华夏，智创未来','venue':'广州越秀国际会议中心','conference_dates':['2026-11-27','2026-11-29'],'registration_dates':['2026-10-18','2026-11-20'],
 'submission_window':{'standard_deadline':'2026-04-10','review_results_notice':'2026-06-01','result_notice_describes_review_complete':True,'current_standard_submission_open':False,'late_or_reopened_call_found':False,'late_window_status':'NO_OFFICIAL_REOPENING_FOUND_IN_THIS_LIMITED_CHECK','interpretation':'当前参会注册仍在通知窗口内，不代表论文征集仍开放；不能承诺本轮新稿能投2026主会。'},
 'submission_portal':'http://paper.planning.cn','unified_login':'https://sso.planning.org.cn','conference_registration_portal':'https://apply.planning.org.cn','format_rules':rules,'not_specified':unknown,
 'relevant_official_topics':[{'number':4,'text':'生态融入城乡发展的规划路径与生态资产价值实现机制探讨','fit':'生态韧性评价格网诊断与绿隔管护的规划应用，可对接该议题；此为主题契合判断，不是录用保证。'},{'number':30,'text':'数据驱动的规划实施评估与动态调整机制研究','fit':'若论文强调评价稳定性与管护核查可作补充联系；单年描述不得称动态实施效应。'}],
 'topic_vs_submission_track':'官方说明参考议题不同于投稿平台分审选题领域；未登录平台核验领域名称，不猜测生态方向编号。',
 'original_attachment_status':{'call_guidelines':'须知作为征文网页内嵌附件全文存在；未发现独立DOCX/PDF模板下载链接。','registration_pdf':'原始会议通知PDF通过官网附件链接获取，见下载回执；它是会议通知，不是论文模板。'},
 'excluded_other_venues':['2026城市交通规划年会（9000字、25字标题、摘要约300字等不用于本稿）','城市生态规划专委会2026武汉年会','求是理论论坛6500–7500字/图表8个规则','中国城市规划协会相关年会','国际中国城市规划学会IACP会议'],
 'sources':[source_call,source_result,source_reg],
 'actions_taken':'只读检索与公开原文归档；未登录、未投稿、未联系会务、未更改目标或正式稿。'}
files=[]
for p in sorted(P.iterdir()):
 if p.is_file() and p.suffix.lower() in ['.html','.pdf','.json','.txt'] and not p.name.startswith('219_'):
  files.append({'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
record['archived_files']=files
save('219_2026规划年会官方格式与窗口核验.json',record)
lines=['2026中国城市规划年会主会：官方格式与窗口核验','核验日期：2026-11-06','',
 '当前窗口：常规征文已于2026-04-10截止，官方6月1日已公告评审完成。本轮没有发现官方补征/重开通知。10月18日至11月20日开放的是参会注册，不能据此称论文仍可投稿。','',
 '已核官方格式：正文8000字以内（不含参考文献）；通栏A4；上下25.4mm、左右31.8mm；主标题≤20字、三号宋体加粗居中；摘要300–500字、关键词3–7个，均小五号楷体；正文五号宋体，首行两格，1.5倍行距。分级标题、注释及参考文献样式见JSON。','',
 '匿名要求：文章、脚注和尾注均不出现作者个人信息，作者信息由平台收集。涉及身份的基金完整版按官方指定流程另行提供；本任务未进行任何提交。','',
 '图表：已核通知明确地图要求，但没有明确图表数量、DPI或图表题字体数字；不能套交通年会或其他分会标准。须知要求注意完整县级以上行政界线等须审核地图。本报告记录会议要求，不代替单幅图的适用性判断。','',
 '主会：2026-11-27至29日，广州越秀国际会议中心；主题为“城市规划70年：经纬华夏，智创未来”。本研究与官方参考议题4（生态融入城乡发展）有关。','',
 '官方来源：',source_call['url'],source_result['url'],source_reg['url'],'',
 '附件：征文须知在官方网页正文内完整列出，未发现独立Word模板。已归档的中规学字〔2026〕22号PDF是参会通知，不应当作论文模板。所有原网页与提取文本保留。',
 '未改正式稿、未变更目标、未投稿；未来投递须依据实际可用窗口再处理。']
(P/'219_2026规划年会核验结论.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('VENUE_CHECK_COMPLETE',len(rules),'verified fields',len(unknown),'not explicit')
