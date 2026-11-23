# KML 标签图钉问题排查记录（供 Codex 接手）

> 本文档完整记录了「扇区图层 KML/KMZ 标签在奥维互动地图中显示为图钉」问题的排查过程、验证矩阵、代码位置与已知结论，供 Codex 快速接手定位解决方案。

---

## 一、问题概述

**软件**：通信规划图层生成工具（PlanLayerCreator）V1.2
**功能**：从基站/小区 Excel 数据生成扇区图层，输出 KML / KMZ / TAB / SHP。

**需求**：扇区图层的 KML/KMZ 中，每个扇区显示「小区名称」文字标签。

**问题**：
- ✅ Google 地球：标签文字正常显示，无图钉（已解决）。
- ❌ 奥维互动地图（OvitalMap）：标签文字旁**多出一个黄色图钉图标**，用户只需要纯文字标签，不要图钉。

---

## 二、环境与技术栈

| 项 | 值 |
|----|-----|
| 项目路径 | `D:\SuperHermes\41_PlanLayerCreator_20260807\publish\PlanLayerCreator` |
| KML 生成库 | `simplekml`（版本见 `D:\SuperCodex\.venvs\planlayercreator-hermes\Lib\site-packages\simplekml`） |
| 核心代码 | `engine/layer_engine.py` → `generate_sector_layer()` 的 KML/KMZ 分支 |
| Python | 3.12.4（纯净 venv `planlayercreator-hermes`） |
| 奥维版本 | 未知（用户桌面客户端） |
| Google 地球 | 桌面版（具体版本未知） |

---

## 三、当前实现

### 3.1 KML 结构（已实现「两个文件夹」分离）

```
扇区图层.kml
├── 📁 扇区   ← 扇区面（Polygon，name=小区名称，配色+属性）
└── 📁 标签   ← 标签（Point，name=小区名称，透明图标）
```

### 3.2 关键代码（`engine/layer_engine.py`，扇区 KML 分支）

模块级常量（透明 PNG data URI）：

```python
# 1×1 透明 PNG（data URI），用于隐藏标签点的图钉图标
_TRANSPARENT_PNG = (
    'data:image/png;base64,'
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
)
```

生成逻辑（简化）：

```python
folder_sectors = kml.newfolder(name='扇区')
folder_labels = kml.newfolder(name='标签') if add_label else None

for idx, (_, row) in enumerate(df.iterrows()):
    # 扇区面 → "扇区"文件夹
    pol = folder_sectors.newpolygon(name=name, outerboundaryis=verts)
    pol.style.polystyle.color = kml_color
    pol.style.linestyle.color = ...
    pol.style.linestyle.width = line_width
    _add_ext_data(pol, row, exclude_cols={...})

    # 标签 → "标签"文件夹（Point）
    if add_label:
        glon, glat = gen.label_position(az, radius)  # 标签位置=扇区内部
        pnt = folder_labels.newpoint(name=name, coords=[(glon, glat)])
        pnt.style.iconstyle.scale = 0                       # 隐藏图标方式1
        pnt.style.iconstyle.icon.href = _TRANSPARENT_PNG    # 隐藏图标方式2
        pnt.style.labelstyle.scale = 1.2                    # 标签文字大小
        pnt.style.labelstyle.color = simplekml.Color.hexa(label_color[1:] + 'ff')
```

生成的标签 Point 实际 KML：

```xml
<Style id="18">
  <IconStyle id="19">
    <colorMode>normal</colorMode>
    <scale>0</scale>
    <heading>0</heading>
    <Icon id="20">
      <href>data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=</href>
    </Icon>
  </IconStyle>
  <LabelStyle id="21">
    <color>ff00FFFF</color>
    <colorMode>normal</colorMode>
    <scale>1.2</scale>
  </LabelStyle>
</Style>
<Placemark id="17"><name>A</name><styleUrl>#18</styleUrl><Point>...</Point></Placemark>
```

---

## 四、完整验证矩阵（已实测，勿重复排查）

在奥维互动地图中逐项测试，结果如下：

| # | 方案 | KML 写法 | 奥维结果 |
|---|------|---------|---------|
| 1 | 点 + scale=0 | `<IconStyle><scale>0</scale></IconStyle>` | ❌ 图钉仍在 |
| 2 | 点 + 透明图标 data URI | `<Icon><href>data:image/png;base64,...透明1x1PNG...</href></Icon>` | ❌ 图钉仍在 |
| 3 | 点 + 本地透明 PNG 文件（打包进 KMZ） | `<Icon><href>transparent.png</href></Icon>` + savekmz 打包 | ❌ 图钉仍在 |
| 4 | 点 + scale=0.01（极小） | `<IconStyle><scale>0.01</scale></IconStyle>` | ❌ 图钉仍在（不缩小） |
| 5 | 点 + 图标颜色全透明 | `<IconStyle><color>00ffffff</color></IconStyle>` | ❌ 图钉仍在 |
| 6 | 面 + name + LabelStyle | `<Polygon>` + `<name>` + `<LabelStyle>` | ❌ 无文字、无图钉（面不显示标签） |
| 7 | 线 + name + LabelStyle | `<LineString>` + `<name>` + `<LabelStyle>` | ❌ 无文字、无图钉（线不显示标签） |

**透明 PNG 有效性已验证**：解码 base64 后确认为 1×1 灰度+alpha PNG，alpha=0（全透明），PNG 本身无问题。

### Google 地球对照行为（同一 KML）

| 几何类型 | Google 地球表现 |
|---------|----------------|
| Point + scale=0 | ✅ 无图钉，有文字（Google 地球认 scale=0） |
| Polygon + name | ❌ 不显示标签（Google 地球对「面」默认不显示 name 标签） |

---

## 五、核心矛盾分析

1. **Google 地球**：对「面」不显示 name 标签 → 必须用「点」承载标签 → 但「点」认 `scale=0` 可隐藏图钉 ✅
2. **奥维**：对「点」**无论任何方式都显示图钉**（不认 scale=0 / 透明图标 / 极小 scale / 透明色）→ 对「面」「线」又不显示 name 文字

**结论**：奥维对 KML 的「纯文字标签（无图钉）」疑似根本不支持，且无法通过标准 KML 方式绕过。

---

## 六、已排除的方向

- ❌ `IconStyle scale=0`
- ❌ 透明图标 data URI（base64 内嵌）
- ❌ 本地透明 PNG 文件 + KMZ 打包
- ❌ `IconStyle scale=0.01`（非零极小值）
- ❌ `IconStyle color` alpha=00（全透明色）
- ❌ 改用 Polygon 的 name 标签（奥维对「面」不显示文字）
- ❌ 改用 LineString 的 name 标签（奥维对「线」不显示文字）

---

## 七、希望 Codex 解决的目标

1. **首选**：找到奥维互动地图中「显示纯文字标签、无图钉」的 KML 写法（是否奥维有私有扩展、`<gx:>` 扩展、`<ExtendedData>` 特殊字段、或特定图标 URL 约定？）。
2. **次选**：找到 Google 地球与奥维**都兼容**的标签方案。
3. **兜底**：若确认奥维对 KML 标签无解，请给出务实替代方案（例如：奥维客户端批量改图标为「无」的操作步骤、或改用奥维原生格式的方案）。

---

## 八、相关文件索引

| 文件 | 说明 |
|------|------|
| `engine/layer_engine.py` | 核心引擎，扇区 KML/KMZ 分支（约第 414-463 行） |
| `utils/sector_utils.py` | 扇区几何生成，`make_sector_vertex_generator` + `label_position` |
| `tabs/sector_tab.py` | 扇区 UI，标签开关 + 标签颜色选择器 |
| `utils/constants.py` | 扇区配色、窗口常量 |

### 关键函数签名

```python
# engine/layer_engine.py
def generate_sector_layer(df, mapping, style, output_path, correct_coords, extra):
    ...
    add_label = extra.get('add_label', True)
    label_color = extra.get('label_color', '#FFFF00')
    ...
```

### 标签位置计算（`utils/sector_utils.py`）

```python
def make_sector_vertex_generator(lon, lat):
    ...
    def gen(azimuth, beamwidth, radius_m, num_points=None):
        ...  # 返回扇区顶点列表
    def label_position(azimuth, radius_m):
        # 标签位置 = 方位角方向、半径一半处（扇区内部）
        rad = math.radians(90 - azimuth)
        d = radius_m * 0.5
        dx = d * math.cos(rad)
        dy = d * math.sin(rad)
        glon, glat = to_wgs.transform(x0 + dx, y0 + dy)
        return glon, glat
    gen.label_position = label_position
    return gen
```

---

## 九、附：真实样本文件

用户实际生成的文件（含完整 IconStyle，供 Codex 直接分析）：
- `C:\Users\Administrator\Desktop\扇区图层\扇区图层-未命名.kml`
- `C:\Users\Administrator\Desktop\扇区图层\扇区图层-未命名.kmz`

测试样例（已生成在桌面 `扇区图层` 文件夹）：
- `测试A_面名称标签.kml` / `测试B_面名称无LabelStyle.kml`
- `测试C_线名称标签.kml` / `测试D_本地透明PNG.kmz`
- `测试E_极小scale.kml` / `测试F_图标全透明色.kml`
