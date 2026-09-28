import glob
import io
import os
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig


class AstrBotHelpDrawer:
    # ---------------- 常量区 ----------------
    FONT_PATH_REGULAR = os.path.join(os.path.dirname(__file__), "DouyinSansBold.otf")
    FONT_PATH_BOLD = FONT_PATH_REGULAR
    LOGO_PATH = os.path.join(os.path.dirname(__file__), "astrbot_logo.jpg")
    # 插件目录下的 fonts/ 文件夹,可放入额外的字体文件(如繁体字体)作为回退字体
    FONT_FALLBACK_DIR = os.path.join(os.path.dirname(__file__), "fonts")

    # 自带字体(抖音美好体)只覆盖简体常用字,遇到繁体字等缺失字形时
    # 按优先级尝试以下系统中文字体进行补齐(Windows / macOS / Linux)
    FALLBACK_FONT_SYSTEM_CANDIDATES = (
        r"%WINDIR%\Fonts\msyh.ttc",
        r"%WINDIR%\Fonts\msyhbd.ttc",
        r"%WINDIR%\Fonts\simhei.ttf",
        r"%WINDIR%\Fonts\Deng.ttf",
        r"%WINDIR%\Fonts\simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansSC-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    )
    # 部分 Linux 发行版目录结构不同,再按文件名模糊搜索一遍
    FALLBACK_FONT_GLOB_PATTERNS = (
        "/usr/share/fonts/*/*Noto*CJK*",
        "/usr/share/fonts/*/*/*Noto*CJK*",
        "/usr/share/fonts/*/*noto*cjk*",
        "/usr/share/fonts/*/*/*noto*cjk*",
        "/usr/share/fonts/*/wqy*",
        "/usr/share/fonts/*/*wqy*",
    )

    # 主题色
    COLOR_BACKGROUND_START = (248, 250, 255)
    COLOR_BACKGROUND_END = (255, 252, 248)
    COLOR_SECTION_HEADER_BG = (240, 242, 248)
    COLOR_CARD_BACKGROUND = (255, 255, 255)
    COLOR_CARD_OUTLINE = (220, 225, 235)
    COLOR_TEXT_HEADER = (0, 40, 100)
    COLOR_TEXT_SUBTITLE = (80, 80, 80)
    COLOR_TEXT_PLUGIN = (0, 60, 130)
    COLOR_TEXT_COMMAND = (10, 70, 140)
    COLOR_TEXT_DESC = (70, 70, 70)
    COLOR_TEXT_FOOTER = (100, 100, 100)
    COLOR_ACCENT = (0, 90, 180)
    COLOR_LOGO_BG_REMOVE = (255, 255, 255)
    LOGO_BG_TOLERANCE = 25

    # 布局尺寸
    IMG_WIDTH = 800
    PADDING = 25
    TOP_AREA_HEIGHT = 120
    TOP_AREA_MIN_NO_LOGO = 80
    HEADER_TEXT_GAP = 5
    LOGO_TARGET_HEIGHT = 65
    SECTION_HEADER_HEIGHT = 50
    SECTION_MARKER_SIZE = 18
    SECTION_MARKER_PADDING = (SECTION_HEADER_HEIGHT - SECTION_MARKER_SIZE) // 2
    SECTION_TITLE_LEFT_MARGIN = SECTION_MARKER_PADDING * 2 + SECTION_MARKER_SIZE
    SECTION_SPACING_BELOW_HEADER = 15
    SECTION_SPACING_AFTER_CARDS = 25
    CARD_PADDING_X = 15
    CARD_PADDING_Y = 12
    CARD_SPACING = 12
    CARD_CORNER_RADIUS = 10
    CARD_INTERNAL_SPACE = 4
    FOOTER_HEIGHT = 40
    TALL_CARD_DESC_LENGTH_THRESHOLD = 100

    # 内边距常量
    CARD_PADDING_TOP = 10
    CARD_PADDING_BOTTOM = 10
    NAME_DESC_SPACING = 12
    

    # ---------------- 构造函数 ----------------
    def __init__(self, config: AstrBotConfig) -> None:
        self.config = config
        self.plugin_display_name = self._load_plugin_display_name()
        self.plugin_version = self._load_plugin_version()
        self.logo_enabled = getattr(self.config, "logo_enable", True)
        self.title_text, self.subtitle_text = self._get_header_texts()
        self._load_fonts()
        self.resized_logo = None
        if self.logo_enabled:
            self._load_logo()
        self.top_area_height = self._calculate_top_area_height()

    def _get_header_texts(self) -> Tuple[str, str]:
        title_text = (
            str(getattr(self.config, "title_help", "") or "").strip()
            or "AstrBot 命令帮助"
        )
        subtitle_text = (
            str(getattr(self.config, "title_desc", "") or "").strip()
            or "可用插件及指令列表"
        )
        return title_text, subtitle_text

    def _calculate_top_area_height(self) -> int:
        if self.logo_enabled:
            return self.TOP_AREA_HEIGHT

        title_h = self._text_ink_height(self.title_text, self.font_title)
        subtitle_h = self._text_ink_height(self.subtitle_text, self.font_subtitle)
        computed = self.PADDING + title_h + self.HEADER_TEXT_GAP + subtitle_h + self.PADDING
        return max(self.TOP_AREA_MIN_NO_LOGO, computed)

    @staticmethod
    def _read_metadata_value(field_name: str) -> str:
        metadata_path = Path(__file__).resolve().with_name("metadata.yaml")
        try:
            for line in metadata_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped.startswith(f"{field_name}:"):
                    continue
                return stripped.split(":", 1)[1].split("#", 1)[0].strip().strip("\"'")
        except Exception as e:
            logger.warning(f"读取 metadata.yaml 字段 {field_name} 失败: {e}")
        return ""

    def _load_plugin_display_name(self) -> str:
        return self._read_metadata_value("display_name") or "Better_help"

    def _load_plugin_version(self) -> str:
        value = self._read_metadata_value("version")
        if value:
            if value.lower().startswith("v"):
                value = value[1:]
            return value
        return "0.0.0"

    # ---------------- 字体 & Logo ----------------
    def _load_fonts(self) -> None:
        try:
            self.font_title = ImageFont.truetype(self.FONT_PATH_BOLD, 36)
            self.font_subtitle = ImageFont.truetype(self.FONT_PATH_REGULAR, 18)
            self.font_plugin_header = ImageFont.truetype(self.FONT_PATH_BOLD, 20)
            self.font_command = ImageFont.truetype(self.FONT_PATH_BOLD, 15)
            self.font_desc = ImageFont.truetype(self.FONT_PATH_REGULAR, 13)
            self.font_footer = ImageFont.truetype(self.FONT_PATH_REGULAR, 12)
        except Exception as e:
            logger.error(f"加载字体时出错: {e}")
            exit()
        # 回退字体相关状态:候选路径列表、按字号懒加载的实例缓存、缺字形检测结果缓存
        self.fallback_font_paths = self._find_fallback_font_paths()
        self._fallback_font_cache: Dict[int, Any] = {}
        self._fallback_load_failed_logged = False
        self._missing_glyph_cache: Dict[Tuple[int, str], bool] = {}

    def _find_fallback_font_paths(self) -> List[str]:
        """收集回退字体候选路径:配置指定 > 插件 fonts/ 目录 > 系统常见中文字体。"""
        candidates: List[str] = []
        custom = str(getattr(self.config, "font_path_fallback", "") or "").strip()
        if custom:
            candidates.append(custom)
        if os.path.isdir(self.FONT_FALLBACK_DIR):
            for name in sorted(os.listdir(self.FONT_FALLBACK_DIR)):
                if name.lower().endswith((".ttf", ".otf", ".ttc")):
                    candidates.append(os.path.join(self.FONT_FALLBACK_DIR, name))
        for path in self.FALLBACK_FONT_SYSTEM_CANDIDATES:
            candidates.append(os.path.expandvars(path))
        for pattern in self.FALLBACK_FONT_GLOB_PATTERNS:
            candidates.extend(sorted(glob.glob(pattern))[:2])
        # 去重并只保留真实存在的文件
        seen, result = set(), []
        for path in candidates:
            if path and path not in seen and os.path.isfile(path):
                seen.add(path)
                result.append(path)
        return result

    def _get_fallback_font(self, size: int):
        """获取指定字号的回退字体实例,没有可用回退字体时返回 None。"""
        if size in self._fallback_font_cache:
            return self._fallback_font_cache[size]
        if not self.fallback_font_paths:
            return None
        for path in self.fallback_font_paths:
            try:
                font = ImageFont.truetype(path, size)
            except Exception:
                continue
            self._fallback_font_cache[size] = font
            logger.info(f"回退字体已启用(补齐自带字体缺失的字形): {path}")
            return font
        # 所有候选都无法加载,清空避免反复尝试
        self.fallback_font_paths = []
        if not self._fallback_load_failed_logged:
            self._fallback_load_failed_logged = True
            logger.warning(
                "回退字体加载失败,自带字体缺失的字形(如繁体字)将无法显示。"
                "可在插件配置 font_path_fallback 中指定字体路径,"
                "或将字体文件放入插件 fonts/ 目录"
            )
        return None

    @staticmethod
    def _glyph_missing(font: ImageFont.FreeTypeFont, ch: str) -> bool:
        """判断字符在字体中是否缺失字形。

        缺失字形渲染为空(.notdef 无墨迹),其 ink bbox 高度为 0;
        空白字符本身也无墨迹,需排除。
        """
        if ch.isspace():
            return False
        try:
            bbox = font.getbbox(ch)
        except Exception:
            return False
        return bbox[3] - bbox[1] <= 0

    def _text_runs(self, text: str, font: ImageFont.FreeTypeFont) -> List[Tuple[str, Any]]:
        """将文本切分为 (片段, 字体) 列表:自带字体缺字形的字符改用回退字体绘制。"""
        fallback = self._get_fallback_font(font.size)
        if fallback is None:
            return [(text, font)]
        runs: List[Tuple[str, Any]] = []
        cur_chars: List[str] = []
        cur_font: Any = font
        for ch in text:
            if not self._glyph_missing(font, ch):
                run_font = font
            elif not self._glyph_missing(fallback, ch):
                run_font = fallback
            else:
                # 两个字体都没有该字形,维持自带字体(与修复前行为一致)
                run_font = font
            if run_font is cur_font:
                cur_chars.append(ch)
            else:
                runs.append(("".join(cur_chars), cur_font))
                cur_chars, cur_font = [ch], run_font
        runs.append(("".join(cur_chars), cur_font))
        return runs

    def _draw_text(self, draw, xy, text: str, font: ImageFont.FreeTypeFont, fill) -> None:
        """按字形覆盖情况分段绘制文本,缺失字形用回退字体补齐。"""
        x, y = xy
        for seg, seg_font in self._text_runs(text, font):
            draw.text((x, y), seg, font=seg_font, fill=fill)
            x += seg_font.getlength(seg)

    def _text_length(self, text: str, font: ImageFont.FreeTypeFont) -> float:
        """计算文本宽度,与 _draw_text 的分段逻辑保持一致。"""
        return sum(seg_font.getlength(seg) for seg, seg_font in self._text_runs(text, font))

    def _load_logo(self) -> None:
        try:
            logo_img = Image.open(self.LOGO_PATH).convert("RGBA")
            img_data = np.array(logo_img)
            r, g, b, a = img_data.T
            white_areas = (
                (r >= self.COLOR_LOGO_BG_REMOVE[0] - self.LOGO_BG_TOLERANCE)
                & (g >= self.COLOR_LOGO_BG_REMOVE[1] - self.LOGO_BG_TOLERANCE)
                & (b >= self.COLOR_LOGO_BG_REMOVE[2] - self.LOGO_BG_TOLERANCE)
                & (a > 128)
            )
            img_data[..., -1][white_areas.T] = 0
            logo_transparent = Image.fromarray(img_data)
            ow, oh = logo_transparent.size
            new_w = int(self.LOGO_TARGET_HEIGHT * ow / oh)
            self.resized_logo = logo_transparent.resize(
                (new_w, self.LOGO_TARGET_HEIGHT), Image.Resampling.LANCZOS
            )
        except Exception as e:
            logger.warning(f"加载或处理 Logo 时出错: {e}")
            self.resized_logo = None

    # ---------------- 文本解析 ----------------
    @staticmethod
    def _parse_single_command_list(text_list) -> List[Tuple[str, str | None]]:
        if isinstance(text_list, list) and text_list and all(
            isinstance(item, dict) for item in text_list
        ):
            commands = []
            for item in text_list:
                cmd = str(item.get("command") or "").strip()
                if not cmd:
                    continue
                desc_raw = item.get("desc")
                desc = str(desc_raw).strip() if desc_raw else None
                commands.append((cmd, desc.splitlines()[0].strip() if desc else None))
            return commands

        commands = []
        lines = (
            text_list.strip().splitlines()
            if isinstance(text_list, str)
            else [ln for ln in text_list if ln.strip()]
        )

        for line in lines:
            raw = line
            stripped = line.strip()
            if not stripped or (stripped.startswith("[") and stripped.endswith("]")):
                continue
            if (raw.startswith("  ") or raw.startswith("\t")) and commands:
                cmd, desc = commands[-1]
                commands[-1] = (cmd, (desc or "") + stripped)
                continue

            # 新命令解析
            parts = None
            for sep in (" : ", " # ", "#", ":"):
                if sep in stripped:
                    parts = stripped.split(sep, 1)
                    break
            if parts and len(parts) == 2:
                cmd = (
                    parts[0][2:].strip()
                    if parts[0].startswith("- ")
                    else parts[0].strip()
                )
                desc = parts[1].strip()
            else:
                cmd = stripped[2:].strip() if stripped.startswith("- ") else stripped
                desc = None
            commands.append((cmd, desc))

        # 只保留描述第一行
        return [(c, (d.splitlines()[0].strip() if d else None)) for c, d in commands]

    def _parse_plugin_commands_sorted_grouped(
        self, plugin_dict: Dict[str, Any]
    ) -> List[Tuple[str, List[Tuple[str, str | None]]]]:

        large_plugins, small_plugins = [], []
        for name, cmds_raw in plugin_dict.items():
            if not cmds_raw:
                continue
             # 如果在黑名单里，跳过
            if name in getattr(self.config, "plugin_blacklist", []):
                continue
            cmds = self._parse_single_command_list(cmds_raw)
            if not cmds:
                continue
            (small_plugins if len(cmds) == 1 else large_plugins).append((name, cmds))

        large_plugins.sort(key=lambda x: len(x[1]), reverse=True)

        grouped_small_plugin = None
        if small_plugins:
            all_small = [c for _, cmds in small_plugins for c in cmds]
            if all_small:
                grouped_small_plugin = ("简易指令", all_small)
                logger.info(f"-> 创建 '简易指令' ({len(all_small)} 条)")

        result = []

        result.extend(large_plugins)
        if grouped_small_plugin:
            result.append(grouped_small_plugin)

        # 添加自定义命令
        custom_list = []
        if getattr(self.config, "custom_cmds", None):
            custom_list = self._parse_single_command_list(self.config.custom_cmds)
            if custom_list:
                result.append(("自定义命令", custom_list))
                logger.info(f"-> 创建 '自定义命令' ({len(custom_list)} 条)")

        return result

    # ---------------- 绘图辅助 ----------------
    @staticmethod
    def _draw_gradient(
        draw,
        width: int,
        height: int,
        start: Tuple[int, int, int],
        end: Tuple[int, int, int],
    ):
        for y in range(height):
            r = int(start[0] + (end[0] - start[0]) * y / height)
            g = int(start[1] + (end[1] - start[1]) * y / height)
            b = int(start[2] + (end[2] - start[2]) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    def _get_text_metrics(
        self, text: str, font: ImageFont.FreeTypeFont, draw
    ) -> Tuple[Tuple[int, int, int, int], Tuple[int, int]]:
        if not text:
            return (0, 0, 0, 0), (0, 0)
        try:
            w = self._text_length(text, font)
            h = self._text_ink_height(text, font)
            if w <= 0 or h <= 0:
                raise ValueError
            return (0, 0, int(w), int(h)), (int(w), int(h))
        except Exception:
            est_w = len(text) * font.size * 0.6
            est_h = font.size * 1.2
            return (0, 0, max(1, int(est_w)), max(1, int(est_h))), (
                max(1, int(est_w)),
                max(1, int(est_h)),
            )

    def _text_ink_height(self, text: str, font: ImageFont.FreeTypeFont) -> int:
        """计算文本墨迹高度:缺失字形由回退字体渲染,需用实际渲染它的字体测量,
        否则纯繁体文本会量出 0 高度,导致卡片布局错乱。"""
        height = 0
        for seg, seg_font in self._text_runs(text, font):
            try:
                bbox = seg_font.getbbox(seg)
            except Exception:
                continue
            height = max(height, bbox[3] - bbox[1])
        return height

    def _draw_rounded_rectangle(
        self, draw, xy, radius, fill=None, outline=None, width=1
    ):
        x1, y1, x2, y2 = xy
        if x1 >= x2 or y1 >= y2:
            return
        radius = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
        if fill:
            draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill)
            draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill)
            draw.pieslice(
                (x1, y1, x1 + 2 * radius, y1 + 2 * radius), 180, 270, fill=fill
            )
            draw.pieslice(
                (x2 - 2 * radius, y1, x2, y1 + 2 * radius), 270, 360, fill=fill
            )
            draw.pieslice(
                (x1, y2 - 2 * radius, x1 + 2 * radius, y2), 90, 180, fill=fill
            )
            draw.pieslice((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 0, 90, fill=fill)
        if outline and width > 0:
            draw.arc(
                (x1, y1, x1 + 2 * radius, y1 + 2 * radius),
                180,
                270,
                fill=outline,
                width=width,
            )
            draw.arc(
                (x2 - 2 * radius, y1, x2, y1 + 2 * radius),
                270,
                360,
                fill=outline,
                width=width,
            )
            draw.arc(
                (x1, y2 - 2 * radius, x1 + 2 * radius, y2),
                90,
                180,
                fill=outline,
                width=width,
            )
            draw.arc(
                (x2 - 2 * radius, y2 - 2 * radius, x2, y2),
                0,
                90,
                fill=outline,
                width=width,
            )
            draw.line([(x1 + radius, y1), (x2 - radius, y1)], fill=outline, width=width)
            draw.line([(x1 + radius, y2), (x2 - radius, y2)], fill=outline, width=width)
            draw.line([(x1, y1 + radius), (x1, y2 - radius)], fill=outline, width=width)
            draw.line([(x2, y1 + radius), (x2, y2 - radius)], fill=outline, width=width)

    # ---------------- 卡片布局（每行最多 4 张） ----------------
    def _layout_cards(
        self,
        sections: List[Tuple[str, List[Tuple[str, str | None]]]],
        draw,
    ) -> List[Dict]:
        layout_info = []
        y_offset = self.top_area_height + self.PADDING
        max_cols = 4
        card_spacing = self.CARD_SPACING
        card_width = (
            self.IMG_WIDTH - self.PADDING * 2 - card_spacing * (max_cols - 1)
        ) // max_cols

        for section_name, cmds in sections:
            # Section Header
            layout_info.append({"type": "header", "name": section_name, "y": y_offset})
            y_offset += self.SECTION_HEADER_HEIGHT + self.SECTION_SPACING_BELOW_HEADER

            row_cards = []
            col_idx = 0
            max_row_height = 0

            for cmd, desc in cmds:
                # 命令文本高度
                _, (w_cmd, h_cmd) = self._get_text_metrics(cmd, self.font_command, draw)

                # 自动换行 desc，每行 12 字符
                wrapped_desc = textwrap.wrap(desc or "", width=12)
                bbox = self.font_desc.getbbox("A")
                line_height = bbox[3] - bbox[1] + self.CARD_INTERNAL_SPACE

                # 卡片总高度
                h_desc_total = len(wrapped_desc) * line_height if wrapped_desc else 0
                card_h = max(
                    self.CARD_PADDING_TOP
                    + h_cmd
                    + self.NAME_DESC_SPACING
                    + h_desc_total
                    + self.CARD_PADDING_BOTTOM,
                    35,
                )

                row_cards.append(
                    {
                        "type": "card",
                        "name": cmd,
                        "desc": desc,
                        "height": card_h,
                    }
                )
                max_row_height = max(max_row_height, card_h)
                col_idx += 1

                # 达到一行或最后一张
                if col_idx == max_cols:
                    for i, card in enumerate(row_cards):
                        card["x"] = self.PADDING + i * (card_width + card_spacing)
                        card["y"] = y_offset
                        card["width"] = card_width
                    layout_info.extend(row_cards)
                    y_offset += max_row_height + card_spacing
                    row_cards = []
                    col_idx = 0
                    max_row_height = 0

            # 剩余不足一行的卡片
            if row_cards:
                for i, card in enumerate(row_cards):
                    card["x"] = self.PADDING + i * (card_width + card_spacing)
                    card["y"] = y_offset
                    card["width"] = card_width
                layout_info.extend(row_cards)
                y_offset += max_row_height + card_spacing

            y_offset += self.SECTION_SPACING_AFTER_CARDS
        return layout_info

    # ---------------- 绘制卡片（每行多张支持） ----------------
    def _draw_cards(self, img: Image.Image, layout_info: List[Dict]) -> None:
        draw = ImageDraw.Draw(img)
        for item in layout_info:
            if item["type"] == "header":
                draw.rectangle(
                    (
                        0,
                        item["y"],
                        self.IMG_WIDTH,
                        item["y"] + self.SECTION_HEADER_HEIGHT,
                    ),
                    fill=self.COLOR_SECTION_HEADER_BG,
                )
                draw.ellipse(
                    (
                        self.SECTION_MARKER_PADDING,
                        item["y"] + self.SECTION_MARKER_PADDING,
                        self.SECTION_MARKER_PADDING + self.SECTION_MARKER_SIZE,
                        item["y"]
                        + self.SECTION_MARKER_PADDING
                        + self.SECTION_MARKER_SIZE,
                    ),
                    fill=self.COLOR_ACCENT,
                )
                self._draw_text(
                    draw,
                    (
                        self.SECTION_TITLE_LEFT_MARGIN,
                        item["y"] + self.SECTION_MARKER_PADDING,
                    ),
                    item["name"],
                    self.font_plugin_header,
                    self.COLOR_TEXT_HEADER,
                )
            elif item["type"] == "card":
                x0, y0 = item["x"], item["y"]
                x1, y1 = x0 + item["width"], y0 + item["height"]
                self._draw_rounded_rectangle(
                    draw,
                    (x0, y0, x1, y1),
                    radius=self.CARD_CORNER_RADIUS,
                    fill=self.COLOR_CARD_BACKGROUND,
                    outline=self.COLOR_CARD_OUTLINE,
                    width=1,
                )
                # name
                self._draw_text(
                    draw,
                    (x0 + self.CARD_PADDING_X, y0 + self.CARD_PADDING_TOP),
                    item["name"],
                    self.font_command,
                    self.COLOR_TEXT_COMMAND,
                )
                if item.get("desc"):
                    wrapped_desc = textwrap.wrap(item["desc"], width=12)
                    y_start = (
                        y0
                        + self.CARD_INTERNAL_SPACE
                        + self._text_ink_height(item["name"], self.font_command)
                        + self.NAME_DESC_SPACING
                    )
                    line_height = (
                        self.font_desc.getbbox("A")[3]
                        - self.font_desc.getbbox("A")[1]
                        + self.CARD_INTERNAL_SPACE
                    )
                    for i, line in enumerate(wrapped_desc):
                        self._draw_text(
                            draw,
                            (x0 + self.CARD_PADDING_X, y_start + i * line_height),
                            line,
                            self.font_desc,
                            self.COLOR_TEXT_DESC,
                        )

    # ---------------- 主函数 ----------------
    def draw_help_image(self, plugin_commands_dict: Dict[str, Any]) -> bytes:
        # 解析插件命令
        sections = self._parse_plugin_commands_sorted_grouped(plugin_commands_dict)

        # 初步计算总高度
        temp_img = Image.new("RGB", (self.IMG_WIDTH, 1000), color=(255, 255, 255))
        draw = ImageDraw.Draw(temp_img)
        layout_info = self._layout_cards(sections, draw)
        total_height = (
            layout_info[-1]["y"]
            + (layout_info[-1]["height"] if "height" in layout_info[-1] else 0)
            + self.FOOTER_HEIGHT
            + self.PADDING
        )
        total_height = int(total_height)
        
        # 创建最终图片
        img = Image.new("RGB", (self.IMG_WIDTH, total_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # 渐变背景
        self._draw_gradient(
            draw,
            self.IMG_WIDTH,
            total_height,
            self.COLOR_BACKGROUND_START,
            self.COLOR_BACKGROUND_END,
        )

        # 绘制标题与简介（可选 logo）
        title_text = self.title_text
        subtitle_text = self.subtitle_text

        if self.logo_enabled and self.resized_logo:
            img.paste(
                self.resized_logo, (self.PADDING, self.PADDING), self.resized_logo
            )
            logo_w, logo_h = self.resized_logo.size
            x_start = self.PADDING + logo_w + 15
            y_start_title = self.PADDING
        else:
            x_start = self.PADDING
            y_start_title = self.PADDING

        y_start_subtitle = (
            y_start_title
            + self._text_ink_height(title_text, self.font_title)
            + self.HEADER_TEXT_GAP
        )
        self._draw_text(
            draw,
            (x_start, y_start_title),
            title_text,
            self.font_title,
            self.COLOR_TEXT_HEADER,
        )
        self._draw_text(
            draw,
            (x_start, y_start_subtitle),
            subtitle_text,
            self.font_subtitle,
            self.COLOR_TEXT_SUBTITLE,
        )

        # 绘制卡片
        self._draw_cards(img, layout_info)

        # 底部版权
        footer_text = f"{self.plugin_display_name} v{self.plugin_version}"
        bbox = draw.textbbox((0, 0), footer_text, font=self.font_footer)
        fw = self._text_length(footer_text, self.font_footer)
        fh = bbox[3] - bbox[1]
        self._draw_text(
            draw,
            (
                self.IMG_WIDTH - fw - self.PADDING,
                total_height - self.FOOTER_HEIGHT + (self.FOOTER_HEIGHT - fh) // 2,
            ),
            footer_text,
            self.font_footer,
            self.COLOR_TEXT_FOOTER,
        )
        # 转成 bytes
        with io.BytesIO() as output:
            img.save(output, format="PNG", optimize=True)
            return output.getvalue()
