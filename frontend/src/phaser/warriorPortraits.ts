/**
 * 像素武将立绘 — 吞食天地2 NES/FC 风格
 * 32×48 像素，3× 缩放显示 → 96×144px
 * 支持武将：孔明 / 子龙 / 仲达 / 周瑜 / 关羽 / 张飞 / 刘备 / 曹操 / 孙权 / 张辽 / 郭嘉 / 黄盖 / 鲁肃 / 通用
 */

export type WarriorId =
  | "kongming"
  | "zhaoyun"
  | "simayi"
  | "zhouyu"
  | "guanyu"
  | "zhangfei"
  | "liubei"
  | "caocao"
  | "sunquan"
  | "zhangliao"
  | "guojia"
  | "huanggai"
  | "lusu"
  | "generic";

export interface WarriorInfo {
  id: WarriorId;
  name: string;
  title: string;
  color: string;
  faction: "蜀" | "魏" | "吴" | "—";
  factionColor: string;
}

export const WARRIORS: Record<WarriorId, WarriorInfo> = {
  kongming:  { id: "kongming",  name: "诸葛孔明", title: "军师·智绝天下", color: "#1060C8", faction: "蜀", factionColor: "#22C55E" },
  zhaoyun:   { id: "zhaoyun",  name: "赵子龙",   title: "常胜将军",       color: "#B0C8DC", faction: "蜀", factionColor: "#22C55E" },
  simayi:    { id: "simayi",   name: "司马仲达", title: "冢虎·深谋远虑", color: "#4C1870", faction: "魏", factionColor: "#3B82F6" },
  zhouyu:    { id: "zhouyu",   name: "周公瑾",   title: "都督·儒将雄才", color: "#C82010", faction: "吴", factionColor: "#F97316" },
  guanyu:    { id: "guanyu",   name: "关云长",   title: "武圣·义薄云天", color: "#186038", faction: "蜀", factionColor: "#22C55E" },
  zhangfei:  { id: "zhangfei", name: "张翼德",   title: "万夫不当之勇",   color: "#282828", faction: "蜀", factionColor: "#22C55E" },
  liubei:    { id: "liubei",   name: "刘玄德",   title: "仁德之主",       color: "#D4A010", faction: "蜀", factionColor: "#22C55E" },
  caocao:    { id: "caocao",   name: "曹孟德",   title: "治世能臣",       color: "#601010", faction: "魏", factionColor: "#3B82F6" },
  sunquan:   { id: "sunquan",  name: "孙仲谋",   title: "坐断东南",       color: "#582898", faction: "吴", factionColor: "#F97316" },
  zhangliao: { id: "zhangliao",name: "张文远",   title: "威震逍遥津",     color: "#485058", faction: "魏", factionColor: "#3B82F6" },
  guojia:    { id: "guojia",   name: "郭奉孝",   title: "鬼才·算无遗策", color: "#203878", faction: "魏", factionColor: "#3B82F6" },
  huanggai:  { id: "huanggai", name: "黄公覆",   title: "苦肉·老当益壮", color: "#784020", faction: "吴", factionColor: "#F97316" },
  lusu:      { id: "lusu",     name: "鲁子敬",   title: "济世·弘毅谦达", color: "#3878A0", faction: "吴", factionColor: "#F97316" },
  generic:   { id: "generic",  name: "佚名将士", title: "征战四方",         color: "#608090", faction: "—", factionColor: "#94A3B8" },
};

/** 根据 agent 显示名匹配武将 */
export function getWarriorForAgent(displayName: string): WarriorId {
  const n = (displayName ?? "").toLowerCase();
  if (n.includes("孔明") || n.includes("kongming") || n.includes("zhuge") || n.includes("诸葛")) return "kongming";
  if (n.includes("子龙") || n.includes("zhaoyun") || n.includes("赵云") || n.includes("zilong")) return "zhaoyun";
  if (n.includes("仲达") || n.includes("simayi") || n.includes("司马") || n.includes("zhongda")) return "simayi";
  if (n.includes("公瑾") || n.includes("周瑜") || n.includes("zhouyu") || n.includes("gongjin")) return "zhouyu";
  if (n.includes("云长") || n.includes("关羽") || n.includes("guanyu") || n.includes("yunchang")) return "guanyu";
  if (n.includes("翼德") || n.includes("张飞") || n.includes("zhangfei") || n.includes("yide")) return "zhangfei";
  if (n.includes("玄德") || n.includes("刘备") || n.includes("liubei") || n.includes("xuande")) return "liubei";
  if (n.includes("孟德") || n.includes("曹操") || n.includes("caocao") || n.includes("mengde")) return "caocao";
  if (n.includes("仲谋") || n.includes("孙权") || n.includes("sunquan") || n.includes("zhongmou")) return "sunquan";
  if (n.includes("文远") || n.includes("张辽") || n.includes("zhangliao") || n.includes("wenyuan")) return "zhangliao";
  if (n.includes("奉孝") || n.includes("郭嘉") || n.includes("guojia") || n.includes("fengxiao")) return "guojia";
  if (n.includes("公覆") || n.includes("黄盖") || n.includes("huanggai") || n.includes("gongfu")) return "huanggai";
  if (n.includes("子敬") || n.includes("鲁肃") || n.includes("lusu") || n.includes("zijing")) return "lusu";
  // hash-based deterministic assignment for variety
  const hash = (displayName ?? "").split("").reduce((a, c) => ((a << 5) - a) + c.charCodeAt(0), 0);
  const ids: WarriorId[] = ["kongming", "zhaoyun", "simayi", "zhouyu", "guanyu", "zhangfei", "liubei", "caocao", "sunquan", "zhangliao", "guojia", "huanggai", "lusu"];
  return ids[Math.abs(hash) % ids.length];
}

// ── Internal helpers ──────────────────────────────────────────────────────────
function r(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, c: string) {
  ctx.fillStyle = c; ctx.fillRect(x, y, w, h);
}
function p(ctx: CanvasRenderingContext2D, x: number, y: number, c: string) {
  ctx.fillStyle = c; ctx.fillRect(x, y, 1, 1);
}
function hl(ctx: CanvasRenderingContext2D, y: number, x1: number, x2: number, c: string) {
  ctx.fillStyle = c; ctx.fillRect(x1, y, x2 - x1 + 1, 1);
}
function vl(ctx: CanvasRenderingContext2D, x: number, y1: number, y2: number, c: string) {
  ctx.fillStyle = c; ctx.fillRect(x, y1, 1, y2 - y1 + 1);
}

// ── Shared colors ─────────────────────────────────────────────────────────────
const BLK = "#080808", WHT = "#F0F0F0", SKIN = "#F0B080", SKND = "#C07840";
const GOLD = "#D4A010", GLDL = "#F8C030", GLDH = "#FFF080";
const GRAY = "#909090", GRYL = "#C8C8C8", GRYD = "#404040";

// ── 孔明 ──────────────────────────────────────────────────────────────────────
function drawKongming(ctx: CanvasRenderingContext2D) {
  const B = "#0C50B8", BD = "#082888", BL = "#3878E0";
  const FG = "#98CC44", FD = "#508820";         // fan green
  const FS = "#9C5020";                         // fan stem

  // bg gradient strips
  r(ctx, 0, 0, 32, 48, "#080C18"); r(ctx, 4, 0, 24, 48, "#101828");

  // — hat (tall scholar cap) —
  r(ctx, 13, 0, 6, 2, BLK); r(ctx, 11, 2, 10, 7, BLK);
  r(ctx,  8, 9, 16, 3, BLK); hl(ctx, 9, 8, 23, GOLD); hl(ctx, 11, 8, 23, GLDL);

  // — hair sides —
  vl(ctx, 10, 12, 20, BLK); vl(ctx, 21, 12, 20, BLK);

  // — face —
  r(ctx, 11, 12, 10, 12, SKIN); hl(ctx, 12, 11, 20, "#F8C8A0");
  // eyebrows
  hl(ctx, 15, 13, 15, BLK); hl(ctx, 15, 17, 19, BLK);
  // eyes
  r(ctx, 13, 16, 2, 2, BLK); p(ctx, 14, 16, WHT);
  r(ctx, 17, 16, 2, 2, BLK); p(ctx, 18, 16, WHT);
  // nose + mouth
  p(ctx, 15, 19, SKND); p(ctx, 16, 19, SKND);
  hl(ctx, 21, 14, 18, SKND);
  // thin mustache & goatee
  p(ctx, 13, 20, BLK); p(ctx, 14, 20, BLK);
  p(ctx, 17, 20, BLK); p(ctx, 18, 20, BLK);
  hl(ctx, 22, 14, 17, BLK); hl(ctx, 23, 15, 16, BLK);

  // — neck + white collar —
  r(ctx, 13, 24, 6, 2, SKIN); r(ctx, 9, 26, 14, 3, WHT);
  hl(ctx, 28, 9, 22, GOLD); hl(ctx, 29, 9, 22, GLDL);

  // — blue robes (body) —
  r(ctx, 6, 29, 20, 19, B);
  r(ctx, 6, 29, 3, 19, BD); r(ctx, 23, 29, 3, 19, BD);
  r(ctx, 12, 29, 8, 12, BL);
  // robe folds
  vl(ctx, 10, 29, 47, BD); vl(ctx, 21, 29, 47, BD);
  // gold belt
  r(ctx, 8, 41, 16, 2, GOLD); r(ctx, 14, 41, 4, 2, GLDH);

  // — feather fan (right side) —
  r(ctx, 24, 25, 1, 12, FS);   // stem
  r(ctx, 25, 17, 5, 8, FG); r(ctx, 25, 25, 5, 8, FD);
  p(ctx, 25, 16, FG); p(ctx, 27, 15, FG); p(ctx, 29, 16, FG);
  // fan outline
  vl(ctx, 24, 16, 24, BLK); hl(ctx, 17, 25, 29, BLK);
}

// ── 子龙 ──────────────────────────────────────────────────────────────────────
function drawZhaoYun(ctx: CanvasRenderingContext2D) {
  const SL = "#B0C8D8", SLD = "#687898", SLL = "#D8EEF8";
  const RED = "#DC1818", CAPE = "#E0ECF8", CAPED = "#889AAA";

  r(ctx, 0, 0, 32, 48, "#080C10"); r(ctx, 4, 0, 24, 48, "#101820");

  // — helmet —
  r(ctx, 9, 0, 14, 11, SL); r(ctx, 9, 0, 14, 2, SLD); // top dark band
  r(ctx, 7, 5, 18, 6, SL); // wider lower helmet
  r(ctx, 7, 10, 18, 2, SLD); // brim
  hl(ctx, 0, 9, 22, SLL); // highlight
  // red plume
  r(ctx, 14, 0, 4, 5, RED); p(ctx, 14, 0, "#FF4040"); p(ctx, 17, 0, "#FF4040");
  // cheek guards
  r(ctx, 7, 7, 2, 5, SLD); r(ctx, 23, 7, 2, 5, SLD);

  // — face —
  r(ctx, 10, 12, 12, 11, SKIN); hl(ctx, 12, 10, 21, "#F8C8A0");
  // fierce eyes
  r(ctx, 11, 14, 3, 2, BLK); p(ctx, 12, 14, WHT);
  r(ctx, 18, 14, 3, 2, BLK); p(ctx, 19, 14, WHT);
  hl(ctx, 13, 11, 13, BLK); hl(ctx, 13, 18, 20, BLK); // brows
  p(ctx, 15, 17, SKND); p(ctx, 16, 17, SKND);
  hl(ctx, 19, 13, 18, SKND); // mouth
  // jaw
  hl(ctx, 22, 11, 20, SKND);

  // — cape (white/light behind shoulders) —
  r(ctx, 5, 23, 22, 25, CAPE); r(ctx, 5, 23, 4, 25, CAPED); r(ctx, 23, 23, 4, 25, CAPED);

  // — silver plate armor —
  r(ctx, 8, 23, 16, 18, SL);
  r(ctx, 8, 23, 3, 18, SLD); r(ctx, 21, 23, 3, 18, SLD);
  r(ctx, 11, 24, 10, 2, SLL); // chest highlight line
  // armor horizontal plates
  hl(ctx, 28, 8, 23, SLD); hl(ctx, 33, 8, 23, SLD); hl(ctx, 38, 8, 23, SLD);
  // pauldrons
  r(ctx, 4, 24, 4, 5, SL); r(ctx, 24, 24, 4, 5, SL);
  hl(ctx, 24, 4, 7, SLL); hl(ctx, 24, 24, 27, SLL);
  // lower armor
  r(ctx, 9, 41, 14, 7, SLD); r(ctx, 11, 42, 10, 5, SL);
  // spear hint on right
  vl(ctx, 29, 0, 47, SLD); vl(ctx, 28, 0, 47, BLK); vl(ctx, 30, 0, 47, SLL);
}

// ── 仲达 ──────────────────────────────────────────────────────────────────────
function drawSimaYi(ctx: CanvasRenderingContext2D) {
  const PRP = "#2C1040", PRPL = "#441868", PRPD = "#160820";
  const JD = "#1A9848", JDL = "#28D060"; // jade

  r(ctx, 0, 0, 32, 48, "#060408"); r(ctx, 4, 0, 24, 48, "#0A0812");

  // — dark ornate hat —
  r(ctx, 12, 0, 8, 3, PRPD); r(ctx, 10, 3, 12, 7, PRPD);
  r(ctx, 8, 10, 16, 2, PRPD); hl(ctx, 10, 8, 23, PRPL);
  // jade ornament
  r(ctx, 14, 1, 4, 3, JD); hl(ctx, 1, 14, 17, JDL);

  // — hair —
  vl(ctx, 9, 12, 22, BLK); vl(ctx, 22, 12, 22, BLK);

  // — face (pale, scheming) —
  r(ctx, 10, 12, 12, 12, "#E8D8C8"); hl(ctx, 12, 10, 21, "#F0E0D0");
  // narrow calculating eyes (low brows)
  hl(ctx, 14, 12, 14, BLK); hl(ctx, 14, 18, 20, BLK);
  r(ctx, 12, 15, 2, 2, BLK); p(ctx, 13, 15, WHT);
  r(ctx, 18, 15, 2, 2, BLK); p(ctx, 19, 15, WHT);
  // furrowed brow center
  p(ctx, 15, 14, PRPD); p(ctx, 16, 14, PRPD);
  p(ctx, 16, 18, "#A08870"); p(ctx, 15, 18, "#A08870"); // nose
  hl(ctx, 20, 13, 18, "#806858"); // tight mouth
  // thin chin beard
  hl(ctx, 21, 14, 17, BLK); hl(ctx, 22, 14, 17, BLK); hl(ctx, 23, 15, 16, BLK);

  // — neck —
  r(ctx, 13, 24, 6, 2, "#E0D0C0");

  // — dark purple robes —
  r(ctx, 6, 26, 20, 22, PRP); r(ctx, 6, 26, 3, 22, PRPD); r(ctx, 23, 26, 3, 22, PRPD);
  r(ctx, 12, 26, 8, 10, PRPL);
  // wide collar
  r(ctx, 9, 26, 14, 3, PRPD); hl(ctx, 26, 9, 22, JD); hl(ctx, 28, 9, 22, JDL);
  // robe folds
  vl(ctx, 10, 26, 47, PRPD); vl(ctx, 21, 26, 47, PRPD);
  // dark sash
  r(ctx, 9, 39, 14, 2, PRPD); r(ctx, 14, 39, 4, 2, JD);
}

// ── 周瑜 ──────────────────────────────────────────────────────────────────────
function drawZhouYu(ctx: CanvasRenderingContext2D) {
  const RD = "#C01C0C", RDL = "#E83A20", GD = "#D49010", GDL = "#F8B820";
  const TL = "#0C7868";

  r(ctx, 0, 0, 32, 48, "#0C0808"); r(ctx, 4, 0, 24, 48, "#180C0C");

  // — red commander helmet —
  r(ctx, 9, 1, 14, 10, RD); r(ctx, 9, 1, 14, 2, RDL); // top highlight
  r(ctx, 7, 7, 18, 4, RD);
  hl(ctx, 7, 9, 22, RDL);
  r(ctx, 8, 11, 16, 2, GD); hl(ctx, 11, 8, 23, GDL); // gold brim
  // gold plume ornament
  r(ctx, 14, 0, 4, 4, GD); p(ctx, 15, 0, GDL); p(ctx, 16, 0, GDL);
  // cheek guards
  r(ctx, 7, 9, 2, 4, RD); r(ctx, 23, 9, 2, 4, RD);

  // — face (handsome, young) —
  r(ctx, 10, 13, 12, 11, SKIN); hl(ctx, 13, 10, 21, "#F8C8A0");
  hl(ctx, 15, 12, 14, BLK); hl(ctx, 15, 18, 20, BLK); // brows
  r(ctx, 12, 16, 2, 2, BLK); p(ctx, 13, 16, WHT);
  r(ctx, 18, 16, 2, 2, BLK); p(ctx, 19, 16, WHT);
  p(ctx, 16, 19, SKND); hl(ctx, 21, 13, 18, SKND);
  // slight smile
  p(ctx, 13, 21, SKND); p(ctx, 19, 21, SKND);

  // — neck + teal scarf —
  r(ctx, 13, 24, 6, 2, SKIN); r(ctx, 9, 26, 14, 3, TL); hl(ctx, 28, 9, 22, GD);

  // — red & gold armor body —
  r(ctx, 7, 29, 18, 19, RD); r(ctx, 7, 29, 3, 19, "#8C1008"); r(ctx, 22, 29, 3, 19, "#8C1008");
  r(ctx, 11, 29, 10, 6, RDL);
  // gold armor lines/trim
  hl(ctx, 29, 7, 24, GD); hl(ctx, 33, 7, 24, GD); hl(ctx, 37, 7, 24, GD);
  // pauldrons with gold trim
  r(ctx, 4, 24, 4, 6, RD); hl(ctx, 24, 4, 7, GDL);
  r(ctx, 24, 24, 4, 6, RD); hl(ctx, 24, 24, 27, GDL);
  // gold belt
  r(ctx, 9, 41, 14, 3, GD); r(ctx, 14, 41, 4, 3, GDL);
}

// ── 关羽 ──────────────────────────────────────────────────────────────────────
function drawGuanYu(ctx: CanvasRenderingContext2D) {
  const GN = "#186038", GND = "#0C3820", GNL = "#28885C";
  const RS = "#C04030", RSD = "#842820"; // red skin
  const BD = "#140808"; // beard

  r(ctx, 0, 0, 32, 48, "#080C08"); r(ctx, 4, 0, 24, 48, "#0C1410");

  // — green military headband/helmet —
  r(ctx, 9, 1, 14, 4, GN); r(ctx, 7, 4, 18, 7, GN);
  r(ctx, 7, 4, 18, 2, GNL); // highlight
  r(ctx, 8, 11, 16, 2, GND); hl(ctx, 11, 8, 23, GOLD);
  // gold headband ornament
  r(ctx, 13, 5, 6, 3, GOLD); hl(ctx, 5, 13, 18, GLDL);

  // — hair —
  vl(ctx, 9, 12, 18, BD); vl(ctx, 22, 12, 18, BD);

  // — reddish face (distinctive!) —
  r(ctx, 10, 13, 12, 10, RS); hl(ctx, 13, 10, 21, "#D85040");
  // strong brows
  hl(ctx, 15, 12, 14, BD); hl(ctx, 15, 17, 20, BD);
  r(ctx, 12, 16, 2, 2, BD); p(ctx, 13, 16, "#FF8080");
  r(ctx, 17, 16, 2, 2, BD); p(ctx, 18, 16, "#FF8080");
  p(ctx, 15, 18, RSD); p(ctx, 16, 18, RSD);
  hl(ctx, 20, 13, 18, RSD);

  // — long magnificent beard —
  r(ctx, 11, 22, 10, 2, BD);  // upper beard
  r(ctx, 10, 24, 12, 4, BD);  // beard wider
  r(ctx, 11, 28, 10, 8, BD);  // long beard flowing down
  r(ctx, 12, 36, 8, 6, BD);   // beard tip
  // beard highlight
  vl(ctx, 15, 24, 40, "#302020"); vl(ctx, 16, 24, 40, "#302020");

  // — neck —
  r(ctx, 13, 22, 6, 2, RS);

  // — green military robe —
  r(ctx, 7, 24, 18, 24, GN); r(ctx, 7, 24, 3, 24, GND); r(ctx, 22, 24, 3, 24, GND);
  r(ctx, 12, 24, 8, 10, GNL);
  vl(ctx, 11, 24, 47, GND); vl(ctx, 20, 24, 47, GND);
  // gold trim
  hl(ctx, 26, 7, 24, GOLD); hl(ctx, 40, 7, 24, GOLD);
  r(ctx, 9, 38, 14, 2, GOLD);
}

// ── 张飞 ──────────────────────────────────────────────────────────────────────
function drawZhangFei(ctx: CanvasRenderingContext2D) {
  const DA = "#181818", DAL = "#302830", DAH = "#484448";
  const EY = "#CC2020"; // fierce eye glow
  const SK = "#D09068";

  r(ctx, 0, 0, 32, 48, "#050505"); r(ctx, 4, 0, 24, 48, "#0C0C0C");

  // — black iron helmet (wide, imposing) —
  r(ctx, 8, 1, 16, 11, DA); r(ctx, 8, 1, 16, 2, DAH);
  r(ctx, 6, 6, 20, 6, DA); hl(ctx, 6, 6, 25, DAH);
  r(ctx, 6, 12, 20, 2, DAL); hl(ctx, 12, 6, 25, GRAY);
  // iron rivets
  p(ctx, 9, 4, DAH); p(ctx, 14, 4, DAH); p(ctx, 18, 4, DAH); p(ctx, 22, 4, DAH);
  // face guards
  r(ctx, 6, 9, 3, 6, DA); r(ctx, 23, 9, 3, 6, DA);

  // — fierce face (wider, darker) —
  r(ctx, 9, 14, 14, 9, SK); hl(ctx, 14, 9, 22, "#E0A878");
  // ferocious eyes - red tinted
  r(ctx, 10, 16, 3, 2, BLK); p(ctx, 11, 16, EY); p(ctx, 12, 16, EY);
  r(ctx, 19, 16, 3, 2, BLK); p(ctx, 19, 16, EY); p(ctx, 20, 16, EY);
  // fierce brows (thick, angled)
  hl(ctx, 15, 10, 12, BLK); hl(ctx, 15, 19, 21, BLK);
  p(ctx, 10, 14, BLK); p(ctx, 11, 14, BLK); p(ctx, 20, 14, BLK); p(ctx, 21, 14, BLK);
  p(ctx, 16, 17, "#A07050"); p(ctx, 15, 17, "#A07050");
  hl(ctx, 20, 11, 20, BLK); // snarling mouth
  p(ctx, 12, 20, BLK); p(ctx, 19, 20, BLK); // teeth gap

  // — wild black beard (thicker than Guan Yu's) —
  r(ctx, 10, 23, 12, 3, BLK);
  r(ctx, 9, 26, 14, 10, BLK); r(ctx, 10, 36, 12, 5, BLK);
  // beard wilder lines
  vl(ctx, 14, 26, 38, "#282020"); vl(ctx, 17, 26, 38, "#282020");

  // — heavy black plate armor —
  r(ctx, 5, 23, 22, 25, DA);
  r(ctx, 5, 23, 4, 25, BLK); r(ctx, 23, 23, 4, 25, BLK);
  r(ctx, 10, 23, 12, 5, DAH);
  // armor horizontal lines
  hl(ctx, 27, 5, 26, DAL); hl(ctx, 31, 5, 26, DAL); hl(ctx, 35, 5, 26, DAL); hl(ctx, 39, 5, 26, DAL);
  // iron pauldrons (massive)
  r(ctx, 2, 22, 6, 8, DA); hl(ctx, 22, 2, 7, DAH); hl(ctx, 26, 2, 7, GRAY);
  r(ctx, 24, 22, 6, 8, DA); hl(ctx, 22, 24, 29, DAH); hl(ctx, 26, 24, 29, GRAY);
  // grimy highlight
  r(ctx, 12, 25, 8, 2, DAH);
}

// ── 刘备 ──────────────────────────────────────────────────────────────────────
function drawLiuBei(ctx: CanvasRenderingContext2D) {
  const GD = "#D4A010", GDL = "#F8C830", GDD = "#A07808";
  const GN = "#2C7030", GND = "#184020";

  r(ctx, 0, 0, 32, 48, "#0C0A04"); r(ctx, 4, 0, 24, 48, "#181408");

  // — golden crown with ear-wings —
  r(ctx, 11, 1, 10, 8, GD); r(ctx, 11, 1, 10, 2, GDL);
  r(ctx, 9, 5, 14, 4, GD);
  // ear-wing flares
  r(ctx, 6, 3, 4, 4, GD); r(ctx, 22, 3, 4, 4, GD);
  p(ctx, 6, 3, GDL); p(ctx, 25, 3, GDL);
  // jade ornament center
  r(ctx, 14, 2, 4, 3, "#28A048"); hl(ctx, 2, 14, 17, "#40D868");
  // brim
  r(ctx, 8, 9, 16, 2, GDD); hl(ctx, 9, 8, 23, GDL);

  // — hair —
  vl(ctx, 10, 11, 20, BLK); vl(ctx, 21, 11, 20, BLK);

  // — face (kind, gentle) —
  r(ctx, 11, 11, 10, 12, SKIN); hl(ctx, 11, 11, 20, "#F8C8A0");
  // gentle brows
  hl(ctx, 14, 13, 15, BLK); hl(ctx, 14, 17, 19, BLK);
  // eyes (calm)
  r(ctx, 13, 15, 2, 2, BLK); p(ctx, 14, 15, WHT);
  r(ctx, 17, 15, 2, 2, BLK); p(ctx, 18, 15, WHT);
  p(ctx, 15, 18, SKND); p(ctx, 16, 18, SKND);
  hl(ctx, 20, 14, 18, SKND);
  // thin mustache
  p(ctx, 13, 20, BLK); p(ctx, 18, 20, BLK);
  hl(ctx, 21, 14, 17, BLK);

  // — neck + green collar —
  r(ctx, 13, 23, 6, 2, SKIN);
  r(ctx, 9, 25, 14, 3, GN); hl(ctx, 25, 9, 22, "#48A058"); hl(ctx, 27, 9, 22, GD);

  // — golden imperial robe —
  r(ctx, 7, 28, 18, 20, GD);
  r(ctx, 7, 28, 3, 20, GDD); r(ctx, 22, 28, 3, 20, GDD);
  r(ctx, 12, 28, 8, 8, GDL);
  vl(ctx, 11, 28, 47, GDD); vl(ctx, 20, 28, 47, GDD);
  // dragon emblem hint
  r(ctx, 13, 32, 6, 4, GND); r(ctx, 14, 33, 4, 2, "#48A058");
  // gold belt
  r(ctx, 9, 40, 14, 2, GDD); r(ctx, 14, 40, 4, 2, GDL);
  // dual swords hint
  vl(ctx, 3, 18, 44, GDD); vl(ctx, 4, 18, 44, GD);
  vl(ctx, 27, 18, 44, GDD); vl(ctx, 28, 18, 44, GD);
}

// ── 曹操 ──────────────────────────────────────────────────────────────────────
function drawCaoCao(ctx: CanvasRenderingContext2D) {
  const DR = "#601010", DRL = "#882020", DRD = "#380808";
  const BKA = "#282020", BKL = "#403030";

  r(ctx, 0, 0, 32, 48, "#080404"); r(ctx, 4, 0, 24, 48, "#100808");

  // — dark red crown (narrow, tall, authoritative) —
  r(ctx, 12, 0, 8, 4, DR); r(ctx, 12, 0, 8, 1, DRL);
  r(ctx, 10, 4, 12, 6, DR);
  r(ctx, 8, 10, 16, 2, DRD); hl(ctx, 10, 8, 23, DRL);
  // gold trim on crown
  hl(ctx, 4, 10, 21, GOLD); hl(ctx, 3, 12, 19, GLDL);

  // — hair —
  vl(ctx, 9, 12, 20, BLK); vl(ctx, 22, 12, 20, BLK);

  // — face (sharp, calculating) —
  r(ctx, 10, 12, 12, 11, SKIN); hl(ctx, 12, 10, 21, "#F8C8A0");
  // sharp brows (angled inward)
  hl(ctx, 14, 11, 14, BLK); hl(ctx, 14, 18, 21, BLK);
  p(ctx, 14, 13, BLK); p(ctx, 18, 13, BLK);
  // narrow eyes
  r(ctx, 12, 15, 2, 2, BLK); p(ctx, 13, 15, WHT);
  r(ctx, 18, 15, 2, 2, BLK); p(ctx, 19, 15, WHT);
  p(ctx, 15, 17, SKND); p(ctx, 16, 17, SKND);
  hl(ctx, 19, 13, 18, SKND);
  // thin beard
  hl(ctx, 20, 14, 17, BLK); hl(ctx, 21, 14, 17, BLK); hl(ctx, 22, 15, 16, BLK);

  // — neck —
  r(ctx, 13, 23, 6, 2, SKIN);

  // — dark red+black armor —
  r(ctx, 6, 25, 20, 23, BKA);
  r(ctx, 6, 25, 3, 23, BLK); r(ctx, 23, 25, 3, 23, BLK);
  r(ctx, 11, 25, 10, 6, BKL);
  // red trim lines
  hl(ctx, 25, 6, 25, DR); hl(ctx, 29, 6, 25, DR); hl(ctx, 34, 6, 25, DR); hl(ctx, 39, 6, 25, DR);
  // pauldrons
  r(ctx, 3, 24, 5, 6, DR); hl(ctx, 24, 3, 7, DRL);
  r(ctx, 24, 24, 5, 6, DR); hl(ctx, 24, 24, 28, DRL);
  // red cape behind
  r(ctx, 4, 30, 3, 18, DRD); r(ctx, 25, 30, 3, 18, DRD);
  // gold belt
  r(ctx, 8, 41, 16, 2, GOLD); r(ctx, 14, 41, 4, 2, GLDL);
}

// ── 孙权 ──────────────────────────────────────────────────────────────────────
function drawSunQuan(ctx: CanvasRenderingContext2D) {
  const PP = "#4C2080", PPL = "#6838A8", PPD = "#2C1048";
  const TG = "#D8A818", TGL = "#F0C838";

  r(ctx, 0, 0, 32, 48, "#060410"); r(ctx, 4, 0, 24, 48, "#0C0818");

  // — purple-gold imperial crown (wide wings) —
  r(ctx, 12, 0, 8, 3, PP); r(ctx, 10, 3, 12, 6, PP);
  r(ctx, 10, 3, 12, 2, PPL);
  // wide wing flares (broader than Liu Bei)
  r(ctx, 5, 4, 6, 4, PP); r(ctx, 21, 4, 6, 4, PP);
  p(ctx, 5, 4, PPL); p(ctx, 26, 4, PPL);
  r(ctx, 8, 9, 16, 2, PPD); hl(ctx, 9, 8, 23, TG);
  // gold ornament
  r(ctx, 14, 1, 4, 3, TG); hl(ctx, 1, 14, 17, TGL);

  // — hair —
  vl(ctx, 9, 11, 20, BLK); vl(ctx, 22, 11, 20, BLK);

  // — face (stern, kingly, with short beard) —
  r(ctx, 10, 11, 12, 12, SKIN); hl(ctx, 11, 10, 21, "#F8C8A0");
  hl(ctx, 14, 12, 14, BLK); hl(ctx, 14, 18, 20, BLK);
  r(ctx, 12, 15, 2, 2, BLK); p(ctx, 13, 15, WHT);
  r(ctx, 18, 15, 2, 2, BLK); p(ctx, 19, 15, WHT);
  p(ctx, 15, 17, SKND); p(ctx, 16, 17, SKND);
  hl(ctx, 19, 13, 18, SKND);
  // short tiger beard
  hl(ctx, 20, 12, 20, BLK); hl(ctx, 21, 13, 19, BLK); hl(ctx, 22, 14, 18, BLK);

  // — neck —
  r(ctx, 13, 23, 6, 2, SKIN);

  // — purple imperial armor —
  r(ctx, 7, 25, 18, 23, PP);
  r(ctx, 7, 25, 3, 23, PPD); r(ctx, 22, 25, 3, 23, PPD);
  r(ctx, 11, 25, 10, 6, PPL);
  // gold armor trim
  hl(ctx, 25, 7, 24, TG); hl(ctx, 30, 7, 24, TG); hl(ctx, 35, 7, 24, TG);
  // gold pauldrons
  r(ctx, 4, 24, 4, 6, PP); hl(ctx, 24, 4, 7, TGL);
  r(ctx, 24, 24, 4, 6, PP); hl(ctx, 24, 24, 27, TGL);
  // gold belt
  r(ctx, 9, 40, 14, 3, TG); r(ctx, 14, 40, 4, 3, TGL);
}

// ── 张辽 ──────────────────────────────────────────────────────────────────────
function drawZhangLiao(ctx: CanvasRenderingContext2D) {
  const IR = "#586068", IRL = "#788088", IRD = "#384048";

  r(ctx, 0, 0, 32, 48, "#080808"); r(ctx, 4, 0, 24, 48, "#101010");

  // — heavy war helmet with cheek guards + spike top —
  r(ctx, 14, 0, 4, 3, IRD); // spike
  r(ctx, 9, 3, 14, 8, IR); r(ctx, 9, 3, 14, 2, IRL);
  r(ctx, 7, 6, 18, 5, IR);
  r(ctx, 7, 11, 18, 2, IRD); hl(ctx, 11, 7, 24, IRL);
  // cheek guards (wide)
  r(ctx, 6, 8, 3, 7, IR); r(ctx, 23, 8, 3, 7, IR);
  hl(ctx, 8, 6, 8, IRL); hl(ctx, 8, 23, 25, IRL);

  // — face (fierce warrior) —
  r(ctx, 10, 13, 12, 10, SKIN); hl(ctx, 13, 10, 21, "#F8C8A0");
  hl(ctx, 15, 11, 14, BLK); hl(ctx, 15, 18, 21, BLK);
  r(ctx, 12, 16, 2, 2, BLK); p(ctx, 13, 16, WHT);
  r(ctx, 18, 16, 2, 2, BLK); p(ctx, 19, 16, WHT);
  p(ctx, 15, 18, SKND); p(ctx, 16, 18, SKND);
  hl(ctx, 20, 13, 18, SKND);
  // jaw
  hl(ctx, 22, 11, 20, SKND);

  // — neck —
  r(ctx, 13, 23, 6, 2, SKIN);

  // — iron plate armor —
  r(ctx, 7, 25, 18, 23, IR);
  r(ctx, 7, 25, 3, 23, IRD); r(ctx, 22, 25, 3, 23, IRD);
  r(ctx, 11, 25, 10, 4, IRL);
  hl(ctx, 28, 7, 24, IRD); hl(ctx, 33, 7, 24, IRD); hl(ctx, 38, 7, 24, IRD);
  // pauldrons
  r(ctx, 4, 24, 4, 6, IR); hl(ctx, 24, 4, 7, IRL);
  r(ctx, 24, 24, 4, 6, IR); hl(ctx, 24, 24, 27, IRL);
  // halberd on right
  vl(ctx, 29, 0, 47, IRD); vl(ctx, 28, 0, 47, BLK); vl(ctx, 30, 0, 47, IRL);
  // gold belt
  r(ctx, 9, 41, 14, 2, GOLD); r(ctx, 14, 41, 4, 2, GLDL);
}

// ── 郭嘉 ──────────────────────────────────────────────────────────────────────
function drawGuoJia(ctx: CanvasRenderingContext2D) {
  const DB = "#203878", DBL = "#3858A0", DBD = "#102048";

  r(ctx, 0, 0, 32, 48, "#040610"); r(ctx, 4, 0, 24, 48, "#080C18");

  // — flat scholar cap (low, refined) —
  r(ctx, 10, 4, 12, 5, DB); r(ctx, 10, 4, 12, 2, DBL);
  r(ctx, 8, 9, 16, 2, DBD); hl(ctx, 9, 8, 23, DBL);

  // — hair (long, flowing) —
  vl(ctx, 9, 11, 22, BLK); vl(ctx, 22, 11, 22, BLK);
  // hair tails
  r(ctx, 8, 16, 2, 8, BLK); r(ctx, 22, 16, 2, 8, BLK);

  // — face (young, pale, brilliant) —
  r(ctx, 10, 11, 12, 12, "#F0D0B8"); hl(ctx, 11, 10, 21, "#F8E0CC");
  // elegant thin brows
  hl(ctx, 14, 12, 14, BLK); hl(ctx, 14, 18, 20, BLK);
  // bright eyes
  r(ctx, 12, 15, 2, 2, BLK); p(ctx, 13, 15, WHT);
  r(ctx, 18, 15, 2, 2, BLK); p(ctx, 19, 15, WHT);
  p(ctx, 15, 17, "#B09888"); p(ctx, 16, 17, "#B09888");
  hl(ctx, 19, 14, 18, "#B09888");
  // faint smile
  p(ctx, 13, 19, "#B09888"); p(ctx, 19, 19, "#B09888");

  // — neck —
  r(ctx, 13, 23, 6, 2, "#F0D0B8");

  // — deep blue scholar robes —
  r(ctx, 7, 25, 18, 23, DB);
  r(ctx, 7, 25, 3, 23, DBD); r(ctx, 22, 25, 3, 23, DBD);
  r(ctx, 12, 25, 8, 8, DBL);
  vl(ctx, 11, 25, 47, DBD); vl(ctx, 20, 25, 47, DBD);
  // white collar
  r(ctx, 9, 25, 14, 3, WHT); hl(ctx, 27, 9, 22, DBL);
  // sash
  r(ctx, 9, 40, 14, 2, WHT); r(ctx, 14, 40, 4, 2, "#E0E0E0");
  // white fan in right hand
  r(ctx, 25, 20, 4, 7, WHT); r(ctx, 25, 20, 4, 1, "#E0E0E0");
  vl(ctx, 24, 20, 26, BLK);
}

// ── 黄盖 ──────────────────────────────────────────────────────────────────────
function drawHuangGai(ctx: CanvasRenderingContext2D) {
  const BN = "#784020", BNL = "#A06030", BND = "#502810";
  const IG = "#505050", IGL = "#787878";

  r(ctx, 0, 0, 32, 48, "#080604"); r(ctx, 4, 0, 24, 48, "#140C08");

  // — wide iron helmet (veteran style) —
  r(ctx, 10, 1, 12, 8, IG); r(ctx, 10, 1, 12, 2, IGL);
  r(ctx, 7, 5, 18, 6, IG);
  r(ctx, 7, 11, 18, 2, BLK); hl(ctx, 11, 7, 24, IGL);
  // rivets
  p(ctx, 9, 4, IGL); p(ctx, 15, 2, IGL); p(ctx, 22, 4, IGL);

  // — face (weathered, old warrior) —
  r(ctx, 10, 13, 12, 10, "#D89868"); hl(ctx, 13, 10, 21, "#E0A878");
  // thick grizzled brows
  hl(ctx, 15, 11, 14, BLK); hl(ctx, 15, 18, 21, BLK);
  r(ctx, 11, 16, 3, 2, BLK); p(ctx, 12, 16, WHT);
  r(ctx, 18, 16, 3, 2, BLK); p(ctx, 19, 16, WHT);
  p(ctx, 15, 18, BND); p(ctx, 16, 18, BND);
  hl(ctx, 20, 12, 19, BND); // grim mouth
  // scar line
  vl(ctx, 20, 14, 19, "#A06838");
  // gray stubble
  hl(ctx, 21, 11, 20, "#505050"); hl(ctx, 22, 12, 19, "#505050");

  // — neck —
  r(ctx, 13, 23, 6, 2, "#D89868");

  // — brown veteran armor —
  r(ctx, 6, 25, 20, 23, BN);
  r(ctx, 6, 25, 3, 23, BND); r(ctx, 23, 25, 3, 23, BND);
  r(ctx, 11, 25, 10, 5, BNL);
  hl(ctx, 29, 6, 25, BND); hl(ctx, 34, 6, 25, BND); hl(ctx, 39, 6, 25, BND);
  // wide pauldrons
  r(ctx, 3, 24, 5, 6, BN); hl(ctx, 24, 3, 7, BNL);
  r(ctx, 24, 24, 5, 6, BN); hl(ctx, 24, 24, 28, BNL);
  // iron chain whip hint
  vl(ctx, 29, 10, 44, IG); p(ctx, 29, 10, IGL); p(ctx, 29, 20, IGL); p(ctx, 29, 30, IGL); p(ctx, 29, 40, IGL);
  // belt
  r(ctx, 8, 41, 16, 2, BND); r(ctx, 14, 41, 4, 2, IG);
}

// ── 鲁肃 ──────────────────────────────────────────────────────────────────────
function drawLuSu(ctx: CanvasRenderingContext2D) {
  const LB = "#3878A0", LBL = "#58A0C8", LBD = "#205068";

  r(ctx, 0, 0, 32, 48, "#040810"); r(ctx, 4, 0, 24, 48, "#081018");

  // — round scholar cap (gentle) —
  r(ctx, 13, 0, 6, 3, LB); r(ctx, 11, 3, 10, 5, LB);
  r(ctx, 11, 3, 10, 2, LBL);
  r(ctx, 9, 8, 14, 3, LB);
  r(ctx, 8, 10, 16, 2, LBD); hl(ctx, 10, 8, 23, LBL);

  // — hair —
  vl(ctx, 10, 12, 20, BLK); vl(ctx, 21, 12, 20, BLK);

  // — face (gentle, diplomatic) —
  r(ctx, 11, 12, 10, 11, SKIN); hl(ctx, 12, 11, 20, "#F8C8A0");
  // gentle brows
  hl(ctx, 15, 13, 15, BLK); hl(ctx, 15, 17, 19, BLK);
  r(ctx, 13, 16, 2, 2, BLK); p(ctx, 14, 16, WHT);
  r(ctx, 17, 16, 2, 2, BLK); p(ctx, 18, 16, WHT);
  p(ctx, 15, 18, SKND); p(ctx, 16, 18, SKND);
  hl(ctx, 20, 14, 17, SKND);
  // thin goatee
  hl(ctx, 21, 15, 16, BLK);

  // — neck + white collar —
  r(ctx, 13, 23, 6, 2, SKIN);
  r(ctx, 9, 25, 14, 3, WHT); hl(ctx, 27, 9, 22, LBL);

  // — light blue scholar robes —
  r(ctx, 7, 28, 18, 20, LB);
  r(ctx, 7, 28, 3, 20, LBD); r(ctx, 22, 28, 3, 20, LBD);
  r(ctx, 12, 28, 8, 8, LBL);
  vl(ctx, 11, 28, 47, LBD); vl(ctx, 20, 28, 47, LBD);
  // scroll in hand
  r(ctx, 24, 24, 5, 4, "#E8E0C8"); r(ctx, 24, 24, 5, 1, "#D0C8A8");
  r(ctx, 24, 27, 5, 1, "#D0C8A8");
  // sash
  r(ctx, 9, 40, 14, 2, LBD); r(ctx, 14, 40, 4, 2, LBL);
}

// ── 通用武将 ─────────────────────────────────────────────────────────────────
function drawGeneric(ctx: CanvasRenderingContext2D) {
  r(ctx, 0, 0, 32, 48, "#080A0C"); r(ctx, 4, 0, 24, 48, "#10141A");
  // helmet
  r(ctx, 9, 1, 14, 11, GRAY); r(ctx, 9, 1, 14, 2, GRYL);
  r(ctx, 7, 7, 18, 5, GRAY); r(ctx, 8, 11, 16, 2, GRYD);
  hl(ctx, 11, 8, 23, GRYL); hl(ctx, 7, 9, 22, "#E0E0E0");
  // face
  r(ctx, 10, 13, 12, 11, SKIN); hl(ctx, 13, 10, 21, "#F8C8A0");
  r(ctx, 11, 15, 3, 2, BLK); p(ctx, 12, 15, WHT);
  r(ctx, 18, 15, 3, 2, BLK); p(ctx, 19, 15, WHT);
  hl(ctx, 14, 12, 14, BLK); hl(ctx, 14, 18, 20, BLK);
  p(ctx, 16, 18, SKND); hl(ctx, 21, 13, 19, SKND);
  // neck + armor
  r(ctx, 13, 24, 6, 2, SKIN);
  r(ctx, 7, 26, 18, 22, GRAY); r(ctx, 7, 26, 3, 22, GRYD); r(ctx, 22, 26, 3, 22, GRYD);
  r(ctx, 11, 26, 10, 5, GRYL);
  hl(ctx, 30, 7, 24, GRYD); hl(ctx, 35, 7, 24, GRYD);
  r(ctx, 4, 24, 4, 5, GRAY); r(ctx, 24, 24, 4, 5, GRAY);
  r(ctx, 10, 40, 12, 2, GOLD);
}

// ── Public API ────────────────────────────────────────────────────────────────
const DRAWERS: Record<WarriorId, (ctx: CanvasRenderingContext2D) => void> = {
  kongming:  drawKongming,
  zhaoyun:   drawZhaoYun,
  simayi:    drawSimaYi,
  zhouyu:    drawZhouYu,
  guanyu:    drawGuanYu,
  zhangfei:  drawZhangFei,
  liubei:    drawLiuBei,
  caocao:    drawCaoCao,
  sunquan:   drawSunQuan,
  zhangliao: drawZhangLiao,
  guojia:    drawGuoJia,
  huanggai:  drawHuangGai,
  lusu:      drawLuSu,
  generic:   drawGeneric,
};

export const PORTRAIT_W = 32;
export const PORTRAIT_H = 48;

/** 将武将立绘渲染到给定 canvas context（native 32×48 坐标，外部 scale） */
export function drawWarriorPortrait(
  ctx: CanvasRenderingContext2D,
  warriorId: WarriorId,
): void {
  ctx.clearRect(0, 0, PORTRAIT_W, PORTRAIT_H);
  DRAWERS[warriorId]?.(ctx);
}

/** 创建独立 canvas 并返回（已绘制，缩放后宽=scale*32, 高=scale*48） */
export function createPortraitCanvas(warriorId: WarriorId, scale = 3): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width  = PORTRAIT_W * scale;
  canvas.height = PORTRAIT_H * scale;
  const ctx = canvas.getContext("2d")!;
  ctx.imageSmoothingEnabled = false;
  ctx.save();
  ctx.scale(scale, scale);
  drawWarriorPortrait(ctx, warriorId);
  ctx.restore();
  return canvas;
}

