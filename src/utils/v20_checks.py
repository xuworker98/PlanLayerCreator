"""Always-on behavior checks for V2.0, also run inside the packaged EXE."""
from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET

def check(value,message):
    if not value:raise AssertionError(message)

def run_checks(output_dir):
    import pandas as pd
    import numpy as np
    import pyogrio.raw
    from PySide6.QtWidgets import QApplication,QScrollArea
    from PySide6.QtGui import QPixmap,QImage
    from main import MainWindow
    from widgets.worker_thread import GenerateWorker
    from engine.layer_engine import generate_grid_layer,generate_drive_layer,_apply_coord_correction
    from engine.gdal_runtime import first_feature_style
    from utils.gcj02 import wgs84_to_gcj02,gcj02_to_wgs84
    from utils.constants import LEVEL_COLORS_6,LEVEL_COLORS_9
    from utils.level_scheme import validate_scheme,contains
    root=Path(output_dir)/'v20';root.mkdir(parents=True,exist_ok=True)
    window=MainWindow()
    check(window.tabs.count()==7,'Missing tab')
    for i in range(6):
        tab=window.tabs.widget(i)
        check(not tab.findChildren(QScrollArea),'Layer page must not contain a scrollbar')
        formats=[tab.format_combo.itemText(j) for j in range(tab.format_combo.count())]
        check(sum('TAB' in text for text in formats)==1,'Multiple TAB choices')
        check('TAB (MapInfo)' in formats,'Unified TAB missing')
        check(not any('兼容' in text or '快速' in text for text in formats),'Implementation choices exposed')
    for direction in ('up','down','left','right'):
        check(not QPixmap(':/res/scroll_'+direction+'.svg').isNull(),'Arrow resource missing')
    for i in (2,3):
        tab=window.tabs.widget(i)
        tab.format_combo.setCurrentText('TAB (MapInfo)')
        check(not tab.transparency_spin.isEnabled(),'Unsupported TAB alpha enabled')
        tab.format_combo.setCurrentIndex(0)
        check(tab.transparency_spin.isEnabled(),'KML alpha disabled')
    df=pd.DataFrame({'lon':[108.37,108.38],'lat':[22.8,22.81],'level':[-120.,-80.],
                     'name':['南宁甲','南宁乙'],'az':[0.,120.],'id':['a','b']})
    mapping={'lon':'lon','lat':'lat','level':'level','grid_id':'id'}
    checks={}
    fixtures={
      'site':(df,{'lon':'lon','lat':'lat','name':'name'}),
      'sector':(df,{'lon':'lon','lat':'lat','name':'name','azimuth':'az'}),
      'drive':(df,{'lon':'lon','lat':'lat','level':'level'}),
      'grid':(df,mapping),
      'line':(pd.DataFrame({'名称':['线甲','线乙'],'WKT':['LINESTRING (108 22,109 23)','LINESTRING (108 23,109 24)']}),{'type_col':'名称','wkt_col':'WKT'}),
      'polygon':(pd.DataFrame({'名称':['面甲','面乙'],'WKT':['POLYGON ((108 22,109 22,109 23,108 22))','POLYGON ((108 23,109 23,109 24,108 23))']}),{'type_col':'名称','wkt_col':'WKT'})}
    for kind,(data,fields) in fixtures.items():
        target=root/(kind+' 中文.tab')
        def worker():
            w=GenerateWorker(kind,data,fields,{'_input_file':'输入示例.csv','_input_sheet':'默认'},str(target))
            errors=[];done=[];w.error.connect(errors.append);w.finished.connect(done.append);w.run()
            check(not errors and done,str(errors));return Path(w.output_path)
        first=worker();digest=hashlib.sha256(first.read_bytes()).digest();second=worker()
        check(first!=second and second.stem.endswith('_2'),'Existing output not renamed')
        check(hashlib.sha256(first.read_bytes()).digest()==digest,'Existing output changed')
        for path in (first,second):
            meta,_,geom,values=pyogrio.raw.read(str(path))
            check(len(geom)==len(data),'TAB count differs')
            log=path.with_name(path.stem+'_结果日志.txt')
            content=log.read_text(encoding='utf-8')
            check('成功' in content and '输入示例.csv' in content and 'Traceback' not in content,'Result log invalid')
        checks[kind+'_tab_new_and_existing']=True
    # A backend failure must leave no published geometry and exactly one concise result log.
    import engine.gdal_runtime as runtime
    original=runtime.mif_to_tab
    try:
        def fail(*args,**kwargs):raise RuntimeError('测试写入失败')
        runtime.mif_to_tab=fail
        target=root/'failure.tab';w=GenerateWorker('site',df,fixtures['site'][1],{},str(target))
        errors=[];w.error.connect(errors.append);w.run()
        check(errors and not target.exists(),'Failed export was published')
        text=(root/'failure_结果日志.txt').read_text(encoding='utf-8')
        check('失败' in text and '测试写入失败' in text and 'Traceback' not in text,'Failure summary invalid')
    finally:runtime.mif_to_tab=original
    ns={'k':'http://www.opengis.net/kml/2.2'}
    for fill in (False,True):
      for outline in (False,True):
        options={'fill_enabled':fill,'outline_enabled':outline,'border_color':'#123456',
                 'border_width':2.5,'transparency':50,'level_colors':validate_scheme(LEVEL_COLORS_6,'left')}
        for ext in ('kml','kmz','tab','mif','shp'):
            target=root/(f'grid_{int(fill)}_{int(outline)}.'+ext)
            check(generate_grid_layer(df,mapping,{},str(target),extra=options)==2,'Grid count differs')
            if ext in ('kml','kmz'):
                if ext=='kmz':
                    with zipfile.ZipFile(target) as z:
                        check('files/legend.png' in z.namelist(),'Grid legend not embedded')
                        tree=ET.fromstring(z.read('doc.kml'))
                else:tree=ET.parse(target).getroot()
                check(tree.find('.//k:ScreenOverlay/k:name',ns).text=='栅格图例','Wrong overlay name')
                check(tree.find('.//k:PolyStyle/k:fill',ns).text==str(int(fill)),'Fill not saved')
                check(tree.find('.//k:PolyStyle/k:outline',ns).text==str(int(outline)),'Outline not saved')
                check(tree.find('.//k:PolyStyle/k:color',ns).text.startswith('80'),'Alpha not saved')
                check(float(tree.find('.//k:LineStyle/k:width',ns).text)==2.5,'Width truncated')
            elif ext=='tab':
                style=first_feature_style(str(target))
                check(f'mapinfo-brush-{2 if fill else 1},' in style,'TAB fill differs')
                check(f'mapinfo-pen-{2 if outline else 1},' in style,'TAB outline differs')
                check('#123456' in style,'TAB border color differs')
            elif ext=='mif':
                text=target.read_text(encoding='gbk')
                check(f'Brush ({2 if fill else 1},' in text,'MIF fill differs')
            else:
                qml=ET.parse(target.with_suffix('.qml')).getroot()
                props={n.get('k'):n.get('v') for n in qml.findall('.//symbols/symbol/layer/prop')}
                check(props['outline_style']==('solid' if outline else 'no'),'QML border differs')
                check(props['color'].split(',')[-1]==('128' if fill else '0'),'QML alpha differs')
        target=root/f'route_{int(fill)}_{int(outline)}.kmz'
        check(generate_drive_layer(df,mapping,{},str(target),extra=options)==2,'Route count differs')
        with zipfile.ZipFile(target) as z:
            from tempfile import TemporaryDirectory
            with TemporaryDirectory(dir=root) as scratch:
                image_path=Path(scratch)/'point.png';image_path.write_bytes(z.read('files/point.png'))
                image=QImage(str(image_path));center=image.pixelColor(16,16)
                check(center.alpha()==(128 if fill else 0),'Point fill alpha differs')
                border_pixels=sum(image.pixelColor(x,y).name()=='#123456' and image.pixelColor(x,y).alpha()>200 for x in range(32) for y in range(32))
                check((border_pixels>0)==outline,'Point border differs')
    checks['grid_and_route_styles_and_legends']=True
    # Product worker must resolve an unknown MIF count, not treat -1 as a mismatch.
    for kind in ('grid','drive'):
        data,fields=fixtures[kind]
        target=root/(kind+'_worker.mif')
        worker=GenerateWorker(kind,data,fields,{},str(target))
        errors=[];worker.error.connect(errors.append);worker.run()
        check(not errors and target.is_file() and target.with_suffix('.mid').is_file(),str(errors))
        import pyogrio
        check(int(pyogrio.read_info(str(target),force_feature_count=True)['features'])==len(data),'MIF count differs')
    # A real count mismatch must still fail and leave the files unpublished.
    import engine.layer_engine as layer_engine
    original_grid=layer_engine.generate_grid_layer
    try:
        def wrong_count(*args,**kwargs):return original_grid(*args,**kwargs)+1
        layer_engine.generate_grid_layer=wrong_count
        target=root/'mif_mismatch.mif'
        worker=GenerateWorker('grid',df,mapping,{},str(target))
        errors=[];worker.error.connect(errors.append);worker.run()
        check(errors and '输出数量核验失败' in errors[0],'Actual MIF mismatch was accepted')
        check(not target.exists() and not target.with_suffix('.mid').exists(),'Mismatched MIF was published')
    finally:layer_engine.generate_grid_layer=original_grid
    # Unknown even after forced counting must fail explicitly.
    original_info=pyogrio.read_info
    try:
        def unknown_count(path,*args,**kwargs):
            if str(path).lower().endswith('.mif'):return {'features':-1}
            return original_info(path,*args,**kwargs)
        pyogrio.read_info=unknown_count
        target=root/'mif_unknown.mif'
        worker=GenerateWorker('grid',df,mapping,{},str(target))
        errors=[];worker.error.connect(errors.append);worker.run()
        check(errors and '无法取得输出要素数量' in errors[0],'Unknown count was accepted')
        check(not target.exists(),'Unknown-count MIF was published')
    finally:pyogrio.read_info=original_info
    polygon_tab=window.polygon_tab
    check(polygon_tab.no_fill_check.isChecked(),'Polygon no-fill default missing')
    check(not polygon_tab.fill_color_btn.isEnabled(),'Disabled fill picker remains active')
    data,fields=fixtures['polygon']
    for suffix in ('kml','tab'):
        target=root/('polygon_default.'+suffix)
        worker=GenerateWorker('polygon',data,fields,polygon_tab.style,str(target),extra=polygon_tab.get_extra_params())
        errors=[];worker.error.connect(errors.append);worker.run();check(not errors,str(errors))
        if suffix=='kml':check(ET.parse(target).find('.//k:PolyStyle/k:fill',ns).text=='0','Default KML polygon is filled')
        else:check('mapinfo-brush-1,' in first_feature_style(str(target)),'Default TAB polygon is filled')
    polygon_tab.no_fill_check.setChecked(False)
    check(polygon_tab.fill_color_btn.isEnabled() and polygon_tab.get_extra_params()['fill_enabled'],'Polygon fill cannot be restored')
    target=root/'polygon_filled.kml'
    worker=GenerateWorker('polygon',data,fields,polygon_tab.style,str(target),extra=polygon_tab.get_extra_params())
    errors=[];worker.error.connect(errors.append);worker.run();check(not errors,str(errors))
    check(ET.parse(target).find('.//k:PolyStyle/k:fill',ns).text=='1','Restored fill not exported')
    checks['mif_unknown_count_resolved_and_real_mismatch_rejected']=True
    checks['polygon_default_no_fill_and_manual_restore']=True
    # All interval boundaries and coordinate modes retain their defined meaning.
    for boundary in ('left','right'):
        colors=validate_scheme(LEVEL_COLORS_9,boundary)
        for threshold in (-120,-115,-112,-110,-105,-100,-90,-80):
            check(sum(bool(contains(threshold,lo,hi,colors)) for lo,hi,_ in colors)==1,'Boundary gap/overlap')
    gcj=wgs84_to_gcj02(108.37,22.8)
    check(max(abs(a-b) for a,b in zip(gcj02_to_wgs84(*gcj),(108.37,22.8)))<2e-8,'Coordinate roundtrip failed')
    check(_apply_coord_correction(df,'lon','lat',False).equals(df),'Original coordinates changed')
    check(not list(root.glob('*运行记录*')) and not list(root.glob('*生成日志*')) and not list(root.glob('错误日志*')),'Extra log files generated')
    checks['single_result_log_and_failure_atomicity']=True
    checks['single_tab_choice_and_resources']=True
    checks['boundaries_and_coordinates']=True
    window.close()
    return checks
