# L2 地图包素材（13 个地区）

由 `tools/worldgen/export_l2_packs.py` 生成。消费方：L2 地区图（战略图下一级）制作、L2 内部地块（L1）Voronoi 细分、地图系统素材。

## 全局文件

| 文件 | 说明 |
|------|------|
| `index_mask_2048.png` | 边界索引图：每地区唯一 RGB 编码（P 社 provinces.bmp 机制，NEAREST 采样），战略图点击查询用 |
| `color_map.json` | 索引图颜色 -> 地区 label 映射 |
| `regions_meta.json` | 全部地区元数据汇总（类型/面积/邻接/多边形/bbox/文件清单） |

## 每地区目录 `region_XXX/`

| 文件 | 分辨率 | 说明 |
|------|--------|------|
| `mask_2048.png` | 2048² | 地区蒙版（白=该地区），与 `region_labels.npy` 一致 |
| `mask_8192.png` | bbox 裁切 | 地区蒙版裁切（与 base/heightmap 像素对齐） |
| `mask_8192_full.png` | 8192² | 地区蒙版全图（全局坐标系） |
| `base_8192.png` | bbox 裁切 | L3 地形底图裁切（preview_fractal.png），含外扩 80px |
| `heightmap_8192.npy` | bbox 裁切 | 高程场 float32（locked_heightmap_8192.npy 裁切），与 base 像素对齐 |
| `heightmap_8192.png` | bbox 裁切 | 高程可视化（人眼检查） |
| `info.json` | - | 地区定位元数据（bbox_8192/质心可派生/邻接/类型/面积/文件清单） |

## 坐标约定

- 全局坐标系：2048（labels）与 8192（底图/高程）两套，`regions_meta.json` 中 `bbox_8192` 为 8192 坐标系
- 裁切文件（base/heightmap/mask 的 bbox 区域）像素一一对齐，可直接叠加
- 从 2048 -> 8192：坐标 × 4；8192 -> 2048：÷ 4

## 消费流程建议

1. 战略图 L2 缩放：加载 `index_mask_2048.png` + `regions_meta.json` 定位地区
2. 进入某地区：加载 `region_XXX/base_8192.png`（L2 底图）+ `mask_8192.png`（裁剪显示）
3. L2 内部细分 L1 地块：用 `heightmap_8192.npy` 做 Voronoi 细分（同 region_split 的 watershed 流程）
