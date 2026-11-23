"""Offline legends shared by route points and MR polygons."""
from pathlib import Path
import tempfile,zipfile,re,shutil
import xml.etree.ElementTree as ET
from urllib.parse import quote
from engine.drive_export import render_legend,render_point,overlay_xml
from utils.constants import LEVEL_COLORS_9,LEVEL_COLORS_6
from utils.level_scheme import validate_scheme


def export_with_legend(implementation,df,mapping,style,output_path,do_correct,extra,progress_cb,point=False):
    target=Path(output_path).absolute();extra=dict(extra or {})
    if target.suffix.lower() not in ('.kml','.kmz'):
        return implementation(df,mapping,style,output_path,do_correct,extra,progress_cb)
    colors=extra.get('level_colors',LEVEL_COLORS_9 if point else LEVEL_COLORS_6)
    colors=validate_scheme(colors,getattr(colors,'boundary',extra.get('boundary','right')))
    extra['level_colors']=colors
    width=int(extra.get('legend_width',360))
    title='路测信号电平' if point else 'MR 栅格电平'
    name='路测图例' if point else '栅格图例'
    suffix=target.suffix.lower();tag=target.stem+'_'+suffix[1:]
    legend_target=target.with_name(tag+'_legend.png')
    if target.exists() or legend_target.exists():raise FileExistsError('同名成果已存在，请另存新名称。')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.plc_legend_',dir=target.parent) as folder:
        folder=Path(folder);staged=folder/('route'+suffix)
        count=implementation(df,mapping,style,str(staged),do_correct,extra,progress_cb)
        legend=folder/'legend.png';render_legend(colors,mapping['level'],legend,title)
        icons={}
        if point:
            for _,_,color in colors:
                if color in icons:continue
                asset='point.png' if not icons else 'point_'+color.lstrip('#')+'.png'
                render_point(folder/asset,color,extra);icons[color]=asset
        def rewrite(payload,nested=False):
            if point:
                def marker(match):
                    element=ET.fromstring(match.group(0));icon=element.find('IconStyle')
                    if icon is None:return match.group(0)
                    color_node=icon.find('color')
                    if color_node is None:return match.group(0)
                    abgr=color_node.text or 'FFFFFFFF'
                    rgb='#'+abgr[6:8]+abgr[4:6]+abgr[2:4]
                    asset=icons.get(rgb.upper(),next(iter(icons.values())))
                    color_node.text='FFFFFFFF'
                    href=icon.find('Icon/href')
                    if href is not None:
                        href.text=(('../files/' if nested else 'files/')+asset if suffix=='.kmz'
                                   else quote(tag+'_'+asset))
                    return ET.tostring(element,encoding='unicode')
                payload=re.sub(r'<Style\b[^>]*>.*?</Style>',marker,payload,flags=re.S)
            if not nested:
                href='files/legend.png' if suffix=='.kmz' else quote(legend_target.name)
                overlay=overlay_xml(href,len(colors),width).replace('路测图例',name)
                payload=payload.replace('</Document>',overlay+'</Document>')
            return payload
        if suffix=='.kmz':
            packed=folder/'packed.kmz'
            with zipfile.ZipFile(staged) as source,zipfile.ZipFile(packed,'w',zipfile.ZIP_DEFLATED) as archive:
                for entry in source.infolist():
                    data=source.read(entry.filename)
                    if entry.filename.endswith('.kml'):data=rewrite(data.decode('utf-8'),'/' in entry.filename).encode('utf-8')
                    archive.writestr(entry,data)
                archive.write(legend,'files/legend.png')
                for asset in icons.values():archive.write(folder/asset,'files/'+asset)
            staged=packed
        else:staged.write_text(rewrite(staged.read_text(encoding='utf-8')),encoding='utf-8')
        pairs=[(legend,legend_target)]
        if suffix=='.kml':pairs += [(folder/asset,target.with_name(tag+'_'+asset)) for asset in icons.values()]
        pairs.append((staged,target))
        if any(destination.exists() for _,destination in pairs):raise FileExistsError('成果配套文件已存在，请另存新名称。')
        for source,destination in pairs:
            with open(source,'rb') as src,open(destination,'xb') as dst:shutil.copyfileobj(src,dst)
        return count
